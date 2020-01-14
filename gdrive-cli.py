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
parser.add_argument('--folder', dest='folder', help='Destination folder id (or folders separated by ,)')
parser.add_argument('--credentials', dest='credentials', help='Credentials file', default='credentials.json')
parser.add_argument('--token', dest='token', help='OAuth access token', default='token.pickle')
parser.add_argument('--filename', help='File to upload')
parser.add_argument('--fileid', help='File to upload')

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


    def list_files(self, folder):
        result = self._service.files().list(fields="files(id, name)", q="'{}' in parents".format(folder)).execute()
        files = result.get('files', [])
        for f in files: print("{id}\t{name}".format(**f))


    def download_file(self, file_id, filename):
        fh = io.FileIO(filename, 'wb')
        request = self._service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        print("Downloading " + filename)
        while done is False:
            status, done = downloader.next_chunk()
        print("\n{} downloaded".format(filename))


    def upload_file(self, filename):
        metadata = {'name': filename}
        if args.folder: metadata['parents'] = args.folder.split(',')
        media = MediaFileUpload(filename, chunksize=1024*1024, resumable=True)
        file = self._service.files().create(body=metadata, media_body=media, fields='id, webViewLink').execute()
        return file


    def set_public(self, file_id):
        metadata = {'role': 'reader', 'type': 'anyone'}
        permission = self._service.permissions().create(fileId=file_id, body=metadata).execute()
        return permission


    def upload_public_file(self, filename):
        file = self.upload_file(filename)
        self.set_public(file['id'])
        return file


if __name__ == '__main__':
    with gdrive() as gdrive:
        if "upload" == args.action:
            print("filename:" + args.filename)
            file = gdrive.upload_public_file(args.filename)
            print("link:{id}\nhash:{webViewLink}".format(**file))
        elif "download" == args.action:
            gdrive.download_file(args.fileid, args.filename)
        elif "list" == args.action:
            gdrive.list_files(args.folder)
