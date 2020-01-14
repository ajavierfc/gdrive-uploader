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
parser.add_argument('action', choices=['list', 'upload', 'download'], help='Action to perform', default='upload')
parser.add_argument('-c', '--credentials', dest='credentials', help='Credentials file (default credentials.json)', default='credentials.json')
parser.add_argument('-t', '--token', help='OAuth access token (default token.pickle)', default='token.pickle')
parser.add_argument('-d', '--folder', dest='folder_id', help='Folder identifier (or folders separated by ,) for uploading or listing')
parser.add_argument('-fn', '--filename', help='File name to upload/download')
parser.add_argument('-f', '--file', dest='file_id', help='File identifier to download')
parser.add_argument('-D', '--drive', dest='drive_id', help='Drive identifier')

args = parser.parse_args()

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive.file']


class gdrive():

    def __init__(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(args.token):
            with open(args.token, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(args.credentials, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(args.token, 'wb') as token:
                pickle.dump(creds, token)

        self._service = build('drive', 'v3', credentials=creds)


    def __enter__(self):
        return self


    def __exit__(self, type, value, tb):
        pass


    def list_files(self, folder_id):
        result = self._service.files().list(fields="files(id, name)", q="'{}' in parents".format(folder_id),
                    pageSize=1000, teamDriveId=args.drive_id, corpora='drive' if args.drive_id else None,
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
        if args.drive_id: metadata['driveId'] = args.drive_id
        if folder_id: metadata['parents'] = folder_id.split(',')
        media = MediaFileUpload(filename, chunksize=1024*1024, resumable=True)
        file = self._service.files().create(body=metadata, media_body=media, fields='id, webViewLink', supportsTeamDrives=True, supportsAllDrives=True).execute()
        return file


    def set_public(self, file_id):
        metadata = {'role': 'reader', 'type': 'anyone'}
        permission = self._service.permissions().create(fileId=file_id, body=metadata, supportsTeamDrives=True, supportsAllDrives=True).execute()
        return permission


    def upload_public_file(self, filename, folder_id):
        file = self.upload_file(filename, folder_id)
        self.set_public(file['id'])
        return file


if __name__ == '__main__':
    with gdrive() as gdrive:
        if "upload" == args.action:
            print("filename:" + args.filename)
            file = gdrive.upload_public_file(args.filename, args.folder_id)
            print("link:{id}\nhash:{webViewLink}".format(**file))

        elif "download" == args.action:
            print("hash:" + args.file_id)
            gdrive.download_file(args.file_id, args.filename)
            print("filename:" + args.filename)

        elif "list" == args.action:
            files = gdrive.list_files(args.folder_id)
            for f in files:
                print("{id}\t{name}".format(**f))
