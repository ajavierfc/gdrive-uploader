#!/usr/bin/python3

from __future__ import print_function
import argparse
import sys
from googledrive import GoogleDrive

# Arguments
parser = argparse.ArgumentParser(description=sys.argv[0])
parser.add_argument('action', choices=['setup', 'list', 'upload', 'download', 'public'], help='Action to perform')
parser.add_argument('-c', '--credentials', dest='credentials', help='Credentials file (default credentials.json)', default='credentials.json')
parser.add_argument('-t', '--token', help='OAuth access token (default token.pickle)', default='token.pickle')
parser.add_argument('-d', '--folder', help='Folder identifier (or folders separated by ,) for uploading or listing')
parser.add_argument('-f', '--file', help='File identifier to download')
parser.add_argument('-fn', '--filename', help='File name to upload/download')
parser.add_argument('-D', '--drive', help='Drive identifier')

args = parser.parse_args()


def upload_public_file(drive, filename, folder_id):
    file = drive.upload_file(filename, folder_id)
    drive.set_public(file['id'])
    return file

def download_folder(drive, folder_id):
    files = drive.list_files(folder_id)
    for file in files:
        if drive.is_folder(file):
            print("folder:{id}\t{name}".format(**file))
        else:
            print("file:{id}\t{mimeType}\nfilename:{name}".format(**file))
            drive.download_file(file['id'], file['name'])


if __name__ == '__main__':

    with GoogleDrive(args.credentials, args.token, args.drive) as drive:
        if "upload" == args.action:
            print("filename:" + args.filename)
            file = upload_public_file(drive, args.filename, args.folder)
            print("file:{id}\nlink:{webViewLink}".format(**file))

        elif "download" == args.action:
            print("file:{}\nfolder:{}".format(args.file, args.folder))
            if args.file:
                drive.download_file(args.file, args.filename)
                print("filename:" + args.filename)
            else:
                download_folder(drive, args.folder)

        elif "public" == args.action:
            drive.set_public(args.file)
            print("link:https://drive.google.com/file/d/{}/view".format(args.file))

        elif "list" == args.action:
            files = drive.list_files(args.folder)
            for f in files:
                print("{id}\t{mimeType}\t{name}".format(**f))
