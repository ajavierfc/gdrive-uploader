#!/usr/bin/python3

from __future__ import print_function
import pickle
import argparse
import os.path
import sys
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Arguments
parser = argparse.ArgumentParser(description=sys.argv[0])
parser.add_argument('action', choices=['nothing', 'list', 'upload', 'download'], help='Action to perform')
parser.add_argument('-c', '--credentials', dest='credentials', help='Credentials file (default credentials.json)', default='credentials.json')
parser.add_argument('-t', '--token', help='OAuth access token (default token.pickle)', default='token.pickle')
parser.add_argument('-d', '--folder', help='Folder identifier (or folders separated by ,) for uploading or listing')
parser.add_argument('-f', '--file', help='File identifier to download')
parser.add_argument('-fn', '--filename', help='File name to upload/download')
parser.add_argument('-D', '--drive', help='Drive identifier')

args = parser.parse_args()

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive.readonly',
          'https://www.googleapis.com/auth/drive.file']

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
        result = self._service.files().list(fields="files(id, name, mimeType)", q="'{}' in parents".format(folder_id),
                    pageSize=1000, teamDriveId=self._drive_id, corpora=self._corpora,
                    supportsTeamDrives=True, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = result.get('files', [])
        return files

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

    def upload_public_file(self, filename, folder_id):
        file = self.upload_file(filename, folder_id)
        self.set_public(file['id'])
        return file


if __name__ == '__main__':
    with GoogleDrive(args.credentials, args.token, args.drive) as drive:
        if "upload" == args.action:
            print("filename:" + args.filename)
            file = drive.upload_public_file(args.filename, args.folder)
            print("file:{id}\nlink:{webViewLink}".format(**file))

        elif "download" == args.action:
            print("file:{}\nfolder:{}".format(args.file, args.folder))
            if args.file:
                drive.download_file(args.file, args.filename)
                print("filename:" + args.filename)
            else:
                files = drive.list_files(args.folder)
                for file in files:
                    if FOLDER == file['mimeType']:
                        print("folder:{id}\t{name}".format(**file))
                    else:
                        print("file:{id}\t{mimeType}\nfilename:{name}".format(**file))
                        drive.download_file(file['id'], file['name'])

        elif "list" == args.action:
            files = drive.list_files(args.folder)
            for f in files:
                print("{id}\t{mimeType}\t{name}".format(**f))
