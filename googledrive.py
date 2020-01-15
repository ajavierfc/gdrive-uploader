#!/usr/bin/python3

from __future__ import print_function
import pickle
import os.path
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
# https://developers.google.com/drive/api/v2/about-auth
SCOPES = ['https://www.googleapis.com/auth/drive', # allow write permissions to any file and download any files
          'https://www.googleapis.com/auth/drive.file'] # allow put files

FOLDER = 'application/vnd.google-apps.folder'

class GoogleDrive():

    def __init__(self, credentials_file, token_file, drive_id):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

        self._service = build('drive', 'v3', credentials=creds)
        self._drive_id = drive_id
        self._corpora = 'drive' if self._drive_id else None

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass

    def list_files(self, folder_id):
        # https://developers.google.com/drive/api/v3/reference/files
        query = "'{}' in parents".format(folder_id) if folder_id else None
        result = self._service.files().list(fields="files(id, name, mimeType)", q=query,
                    pageSize=1000, teamDriveId=self._drive_id, corpora=self._corpora,
                    supportsTeamDrives=True, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = result.get('files', [])
        return files

    def is_folder(self, drive_file):
        return FOLDER == drive_file['mimeType']

    def download_file(self, file_id, filename):
        fh = io.FileIO(filename, 'wb')
        request = self._service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

    def upload_file(self, filename, folder_id):
        metadata = {'name': filename}
        if self._drive_id: metadata['driveId'] = self._drive_id
        if folder_id: metadata['parents'] = folder_id.split(',')
        media = MediaFileUpload(filename, chunksize=1024*1024, resumable=True)
        file = self._service.files().create(body=metadata, media_body=media, fields='id, webViewLink',
                    supportsTeamDrives=True, supportsAllDrives=True).execute()
        return file

    def set_public(self, file_id):
        metadata = {'role': 'reader', 'type': 'anyone'}
        permission = self._service.permissions().create(fileId=file_id, body=metadata,
                        supportsTeamDrives=True, supportsAllDrives=True).execute()
        return permission
