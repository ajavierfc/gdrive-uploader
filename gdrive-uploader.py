#!/usr/bin/python3

from __future__ import print_function
import pickle
import argparse
import os.path
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Arguments
parser = argparse.ArgumentParser(description=sys.argv[0])
parser.add_argument('--folder', dest='folder', help='Destination folder id (or folders separated by ,)')
parser.add_argument('--credentials', dest='credentials', help='Credentials file', default='credentials.json')
parser.add_argument('--token', dest='token', help='OAuth access token', default='token.pickle')
parser.add_argument('filename', help='File to upload')

args = parser.parse_args()


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive.file',
         ]


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
    print("uploading:" + args.filename)
    file = gdrive().upload_public_file(args.filename)
    print("link:{id}\nhash:{webViewLink}".format(**file))
