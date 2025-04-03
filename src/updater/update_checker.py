import os

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QMessageBox, QProgressDialog

from version import VERSION


class UpdateManager(QWidget):
    def __init__(self):
        super().__init__()
        self.current_version = VERSION
        self.latest_version = None
        self.update_available = False

    def check_for_updates(self):
        try:
            res = requests.get('https://api.github.com/repos/Bobsunnet/videoConcat/releases/latest')
            if res.status_code != 200:
                QMessageBox.warning(self, "Error", "Failed to check for updates")
                return

            if res.json()['tag_name'] > VERSION:
                self.latest_version = res.json()['tag_name']
                self.update_available = True
                self.show_update_dialog(res.json()['assets'][0]['browser_download_url'])

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to check for updates: \n{str(e)}")

    def show_update_dialog(self, url:str):
        msg = QMessageBox()
        msg.setText(f"Update available: {self.latest_version}\n\nDownload now?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.download(url)

    def download(self, url:str):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            filename = url.split('/')[-1]

            progress_bar = QProgressDialog("Downloading update...", "Cancel", 0, total_size, self)
            progress_bar.setWindowModality(Qt.WindowModality.WindowModal)
            progress_bar.setAutoClose(True)

            with open(filename, 'wb') as f:
                downloaded = 0
                chunk_size = 8192

                for chunk in response.iter_content(chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress_bar.setValue(downloaded)
                        if progress_bar.wasCanceled():
                            f.close()
                            os.remove(filename)
                            return
            QMessageBox.information(self, "Update Downloaded", f"Update downloaded to {filename}, "
                                                               f"restart application manually from downloaded file.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to download update: \n{str(e)}")


if __name__ == '__main__':
    pass