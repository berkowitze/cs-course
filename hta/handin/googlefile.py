import googleapiclient
import io
import os
from googleapi import drive_api
from apiclient.discovery import Resource
from googleapiclient.http import MediaIoBaseDownload


class GoogleFile:
    def __init__(self, google_id: str, drive: Resource = drive_api()) -> None:
        self.gid = google_id
        self.drive = drive
        self.name = self.drive.files().get(fileId=self.gid).execute()['name']

    def download(self, path: str):
        request = self.drive.files().get_media(fileId=self.gid)
        fh = io.FileIO(path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        try:
            while done is False:
                status, done = downloader.next_chunk()
        # if downloading fails it is due to empty file submission
        except googleapiclient.errors.HttpError:
            with open(path, 'a'):
                os.utime(path)  # make empty file

        self.downloaded = True
        self.dl_path = path
