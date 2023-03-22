import os
import pandas as pd
from tqdm import tqdm
import requests
import xmltodict
import time
from urllib.request import urlretrieve


def download_scheme_images(applno_list, download_root_dir):
    """
    Description:
    디자인권 등록번호 리스트에 포함되는 물품들의 도면 이미지를 다운로드하는 Function
    KIPRIS PLUS API(이하 API)를 활용해 도면 이미지를 다운로드 받기 위한 input 값은 디자인권 "출원번호"다.
    TIPA에서는 디자인권 "등록번호"를 제공하므로, 디자인권 "등록번호"를 디자인권 "출원번호"로 변환하는 프로세스가 필요하다.

    :param applno_list: 디자인권 "등록번호"가 저장되어 있는 csv 파일의 경로
    :param download_root_dir: 다운로드가 될 장소
         scheme_imgs <- download_root_dir
            |- 3008376750000
    """

    # 디자인권 등록번호를 API 활용이 가능하도록 변환 (알파벳 또는 특수기호가 존재하는 경우)
    for register_num in tqdm(applno_list):
        try:
            # 디자인권 등록번호 : 디자인권 출원번호(applyno), 저장을 위한 번호(save_num), 디자인권 우선번호(prior_num)
            applyno, save_num, prior_num = preprocess_register_num(register_num)
            # 도면 이미지 다운로드 및 경로 이동
            download_dir = os.path.join(download_root_dir, save_num)
            if not os.path.isdir(download_dir):
                os.makedirs(download_dir, exist_ok=True)

                # 폴더가 존재하지 않아야 다운로드 함
                download_images(applyno, save_num, prior_num, download_dir)
        except Exception as e:
            print('예외 발생 : ' + register_num + e)


def download_images(applyno, save_num, prior_num, download_dir):
    """
    Description:
    디자인권 출원번호를 입력받아 지정된 경로에 도면 데이터셋을 다운로드하는 function

    상세 프로세스
    1. 디자인권 출원번호를 API에 입력해 도면 다운로드 링크를 얻는다.
    2. 도면 다운로드 링크로부터 도면 이미지를 다운로드한다. (저장 경로 : download_path)
    3. download_path의 도면 이미지를 "../datasets/scheme_imgs/{등록번호}" 폴더로 이동시킨다.
    4. 웹 브라우저를 통한 다운로드 및 파일 이동 간에 속도 차이가 있을 수 있으므로, 일정 시간 동안 멈춘 후 다음 물품으로 넘어간다.

    :param applyno: 디자인권 출원번호
    :param save_num: 디자인권 등록번호 기반의 저장될 폴더 명
    :param prior_num: 디자인권 우선번호 - DM/201230(M003) 중 M003 // DM/089573(001) 중 001
    :param download_dir: 이미지가 다운로드 될 장소
     scheme_imgs
        |- 3008376750000 <- download_dir

    """
    # 다운로드 url
    key = "x8uAiOnARkXIVlmX8TBowTWxB73bU4L3cRNPbN7rUEg="
    # 디자인 도면 다운로드 url
    url1 = "http://plus.kipris.or.kr" \
           "/kipo-api/kipi/designInfoSearchService/getSixImageInfoSearch"
    url2 = "?applicationNumber=" + str(applyno)
    url3 = "&ServiceKey=" + key
    design_url = url1 + url2 + url3

    # REST API 호출
    response = requests.get(design_url)
    content = response.content

    # XML 형태를 DICT(딕셔너리) 형태로 변형후 파일 이름과 경로를 가져옵니다.
    dict_type = xmltodict.parse(content)
    

    ########### DELETEME : 실패에 대한 예외 검토 ###########
    print(dict_type['successYN'])
    if dict_type['successYN'] == 'N':
        print(dict_type)
    ####################################################

    try:
        body = dict_type['response']['body']
    except Exception as e:
        print(dict_type)
        return;

    info_df = info2df(body, prior_num)

    # 도면 이미지 다운로드 -> 국내 특허와 해외 특허의 경우 api 호출 결과값이 달라 구분하여 다운로드
    info_df['save_path'] = info_df.imageName.map(lambda name: os.path.abspath(os.path.join(download_dir, name)))

    for ind, row in info_df.iterrows():
        urlretrieve(row.largePath, row.save_path)


def preprocess_register_num(register_num):
    """
    Description:
    디자인권 등록번호를 전처리하는 Function
    디자인권 등록번호를 "디자인권 출원번호", "저장을 위한 번호", "디자인권 우선 번호" 로 변환하는 기능을 한다.

    상세 프로세스
    1. 디자인권 등록번호 중 해외 특허는 알파벳 및 특수기호가 들어가는 경우가 있어 이를 API를 활용할 수 있도록 변환한다.
    2. 디자인권 등록번호 중, 우선 번호가 존재하는 경우 우선번호를 따로 추출한다.
    2. 디자인권 등록번호에 해당되는 도면이 저장될 폴더를 "등록번호" 이름으로 생성한다.
    3. 디자인권 등록번호를 디자인권 "출원번호"로 변환한다. (해외 특허의 경우 "appReferenceNumber"로 출원번호를 대체할 수 있다.)

    :param register_num:
    :return:
    """
    # 해외 특허 등록 번호 [DM/000000(003)] > API 입력용 등록 변호로 변환
    register_num = str(register_num)
    if len(register_num.split("(")) > 1:
        if len(register_num.split("(")[-1]) == 4:
            prior_num = "M" + register_num.split("(")[-1][:3]
        elif len(register_num.split("(")[-1]) == 5:
            prior_num = register_num.split("(")[-1][:4]
        reg_num = register_num.split("(")[0]
    else:
        reg_num = register_num

    # 디자인권 등록번호에 "/"가 들어가는 경우, 저장 경로에 에러가 발생할 수 있으므로, "/"를 "-"로 대체
    save_num = reg_num
    if "/" in save_num:
        save_num = save_num.replace('/', '-')

    # key : API 활용을 위해 필요한 계정 정보 - KCNET 계정 사용 중
    key = "x8uAiOnARkXIVlmX8TBowTWxB73bU4L3cRNPbN7rUEg="

    # 등록번호 -> 출원번호 변환 url
    url = f"http://plus.kipris.or.kr/kipo-api/kipi/designInfoSearchService/getAdvancedSearch?free={reg_num}&etc=true&part=true&simi=true&open=true&rejection=true&destroy=true&cancle=true&notice=true&registration=true&invalid=true&abandonment=true&ServiceKey={key}"

    # REST API 호출
    response = requests.get(url)
    content = response.content
    # XML 형태를 DICT(딕셔너리) 형태로 변경
    dict_type = xmltodict.parse(content)
    
    # 결과에서 body 부분만 추출
    body = dict_type['response']['body']
    # 해외 특허의 경우, 'appReferenceNumber"를 통해 출원번호를 대체할 수 있다.
    if isinstance(body['items']['item'], list):
        idx = 0
        for i, it in enumerate(body['items']['item']):
            if prior_num in it['designNumber']:
                idx = i
        applyno = body['items']['item'][idx]['appReferenceNumber']
    elif "DM" in reg_num:
        applyno = body['items']['item']['appReferenceNumber']
    else:
        applyno = body['items']['item']['applicationNumber']
        prior_num = body['items']['item']['designNumber']
    return applyno, save_num, prior_num


def info2df(url_dict, prior_number):
    """
    Description:
        kipris 등록번호 도면 이미지 정보를 dict 구조를 df 구조로 변환합니다.
        자세한 정보는 아래 url_dict 구조를 참조하세요.

        변환 후 제공되는 DataFrame 구조는 아래와 같습니다.

        imageName | largePath | number |  smallPath
        000.jpg | http:// ... | 0 | http:// ...

        imageName : 이미지 이름
        largePath : 크기가 큰 도면 이미지 링크
        number  : 도면 순서
        smallPath : 크기가 작은 도면 이미지 링크

        # 등록번호 13자리
        url_dict 구조: Case A
            {item :
                {item :
                    {'imagePath': [{
                        'imageName': '000.jpg', #
                        'largePath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=aed43a0609e94...a156'},
                        'number': '0',
                        'smallPath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=ed43a0...123d }

                        {'imageName': '001.jpg',
                        'largePath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=aed43a0609e94...a156'},
                        'number': '1',
                        'smallPath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=ed43a0...123d }
                        ]
                    }
                }
            }

        url_dict 구조: Case B
                    {item :
                        {item :
                            [{'designNumber': 001,
                             'imagePath': [{
                                'imageName': '000.jpg', #
                                'largePath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=aed43a0609e94...a156'},
                                'number': '0',
                                'smallPath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=ed43a0...123d }

                                {'imageName': '001.jpg',
                                'largePath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=aed43a0609e94...a156'},
                                'number': '1',
                                'smallPath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=ed43a0...123d
                                }],
                            [{'designNumber': 002,
                             'imagePath': [{
                                'imageName': '000.jpg', #
                                'largePath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=aed43a0609e94...a156'},
                                'number': '0',
                                'smallPath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=ed43a0...123d }

                                {'imageName': '001.jpg',
                                'largePath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=aed43a0609e94...a156'},
                                'number': '1',
                                'smallPath': 'http://plus.kipris.or.kr/kiprisplusws/fileToss.jsp?arg=ed43a0...123d
                                }]
                            }]
                        }
                    }

    Args:
        :param dict url_dict: 구조는 위 desc 참조
        :param str prior_number: 'M001'

    """
    # Case A (구조는 desc 참조)
    if isinstance(url_dict['items']['item'], dict):
        scheme_infos = url_dict['items']['item']['imagePath']
        scheme_infos_df = pd.DataFrame(scheme_infos)

    # Case B (구조는 desc 참조)
    elif isinstance(url_dict['items']['item'], list):
        tmp_df = pd.DataFrame(url_dict['items']['item'])
        mask = tmp_df.designNumber.str.contains(prior_number)
        path = tmp_df.loc[mask].imagePath.values[0]
        scheme_infos_df = pd.DataFrame(path)
    else:
        raise NotImplementedError
    return scheme_infos_df
