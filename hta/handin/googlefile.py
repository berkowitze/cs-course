import json
import io
from googleapi import drive_api
from googleapiclient.http import MediaIoBaseDownload
import googleapiclient

drive = drive_api()

class GoogleFile:
    def __init__(self, google_id, drive=drive):
        self.gid = google_id
        self.drive = drive
        self.name = self.get_name()

    def download(self, path):
        request = drive.files().get_media(fileId=self.gid)
        fh = io.FileIO(path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while done is False:
            try:
                status, done = downloader.next_chunk()
            except googleapiclient.errors.HttpError:
                import os
                with open(path, 'a'):
                    os.utime(path, None)

                done = True

        self.downloaded = True
        self.dl_path = path

    def get_name(self):
        return self.drive.files().get(fileId=self.gid).execute()['name']


if __name__ == '__main__':
    file = GoogleFile(f_id, drive)
    file.download('/Users/Eli/Desktop/incredible.arr')
    print file.name
