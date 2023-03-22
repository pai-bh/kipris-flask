from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
import pandas as pd
from kipris_plus_api_v3 import download_scheme_images
app = Flask(__name__)


DOWNLOAD_PATH = "scheme_light"


@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/upload')
def unpload():
    return render_template("upload.html")

# 파일업로드 처리
@app.route('/fileUpload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']

        # TODO : 어떤식으로 받아와야하는지 모르겠음
        download_path = request.values.get("folder_path")
        download_path = "./scheme_light"

        #저장할 경로 + 파일명
        f.save(secure_filename(f.filename))

        # TODO : 파일명에 대한 검토 (csv 및 엑셀파일 등에 대한 확장자를 활용해야할듯)
        assert 'product' in f.filename

        # Kiri Plus API로 전송
        # TODO : 현재 테스트용으로 한건만 전송함
        # TODO : 2023/03/22 기준 Kipris API문제로 인해 정상작동 안됨
        df = pd.read_csv(f.filename, header=None)
        download_scheme_images(df.loc[:1, 0], download_path)


        return '이미지 다운로드 완료'


if __name__ == '__main__':
    app.run()
