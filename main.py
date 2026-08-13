import os
import datetime
import smtplib
import re
import urllib3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import pandas as pd

# SSL 경고 메시지 비활성화 (일부 공학회/대학 사이트 SSL 에러 방지)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------
# [설정] 수집 대상 최적화 키워드 목록
# ---------------------------------------------------------
KEYWORDS = [
    # --- [기업 키워드] ---
    # 1. 자동차 계열 (완성차, 계열사 및 주요 1차 벤더)
    '현대자동차', '현대차', '기아', '현대모비스', '모비스', '현대위아', '현대트랜시스', 
    '현대케피코', '현대오토에버', 'HL만도', '만도', '한온시스템', '에스엘', 'SL', 
    '서연이화', '화신', '성우하이텍', 'CTR', '센트랄', '유라코퍼레이션', '경방신약', 
    '계양전기', '동희', '아신', '코라오', '세방전지', 'DAS', '다스', 'KGM', 'GM',
    '테슬라코리아', '테슬라', '르노자동차', '폭스바겐'

    # 2. HD현대 및 주요 조선/해양 기업
    'HD현대', 'HD현대중공업', 'HD한국조선해양', 'HD현대미포', 'HD현대삼호', 
    'HD현대마린솔루션', 'HD현대일렉트릭', '삼성중공업', '한화오션', '대한조선', 
    '케이조선', 'HJ중공업', '강덕', '선광',

    # --- [직무/기술/분야 키워드] ---
    # 직무
    '부품구매', '부품개발', '구매', 'PM', '생산관리', '생산기술', '품질', '품질관리', '품질보증',
    '설계', '차량설계', 'R&D', '연구개발', '생산', '제조',
    
    # 도메인/전공
    '자동차', '조선', '해양', '배터리', '자율주행', 'HW', '하드웨어', '재료', '금속', '재료공학', '신소재', '선박',
    
    # 채용 형태/조건
    '인턴', '현장실습', '채용연계형', '일경험', '부트캠프', '우대', '공모전', '우대사항', '신입'
]

results = []

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_text(text):
    if not text:
        return ""
    text = text.replace('|', '&#124;')
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def add_result(source, title, link, date="-"):
    if not title or not isinstance(title, str):
        return
    title_clean = clean_text(title)
    if len(title_clean) < 3:
        return
    
    # 키워드 포함 여부 검사
    if any(keyword in title_clean for keyword in KEYWORDS):
        results.append({
            '출처': clean_text(source),
            '제목': title_clean,
            '링크': link.strip(),
            '등록일': clean_text(date)
        })

# ---------------------------------------------------------
# 기존 및 추가 사이트 스크래퍼 함수 (1~23)
# ---------------------------------------------------------
def scrape_linkareer():
    try:
        url = "https://api.linkareer.com/api/v1/activity/list?page=1&perPage=30&sort=CREATED_AT_DESC"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get('data', {}).get('activities', {}).get('nodes', [])
            for item in items:
                add_result('링커리어', item.get('title', ''), f"https://linkareer.com/activity/{item.get('id', '')}")
            print(f"✅ 링커리어 수집 완료 (항목 수: {len(items)})")
    except Exception as e:
        print(f"❌ 링커리어 수집 실패: {e}")

def scrape_jasoseol():
    try:
        url = "https://jasoseol.com/api/v1/employment/list"
        headers = HEADERS.copy()
        headers['Referer'] = 'https://jasoseol.com/'
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            employments = data.get('employments', [])
            for item in employments:
                company = item.get('company_name', '')
                title = item.get('title', '')
                full_title = f"[{company}] {title}" if company else title
                link = f"https://jasoseol.com/recruit/{item.get('id', '')}"
                end_date = str(item.get('end_date', '-'))[:10] if item.get('end_date') else '-'
                add_result('자소설닷컴', full_title, link, end_date)
            print(f"✅ 자소설닷컴 수집 완료 (항목 수: {len(employments)})")
    except Exception as e:
        print(f"❌ 자소설닷컴 수집 실패: {e}")

def scrape_incruit():
    try:
        count = 0
        for kw in ['인턴', '품질', '채용', '현대', '조선']:
            url = f"https://search.incruit.com/list/search.asp?kw={kw}"
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select('div.n_job_list_table ul > li')
                for item in items:
                    title_tag = item.select_one('a.title') or item.select_one('span.cell_mid a')
                    if title_tag:
                        link = title_tag.get('href', '')
                        if not link.startswith('http'):
                            link = 'https:' + link if link.startswith('//') else 'https://job.incruit.com' + link
                        add_result('인크루트', title_tag.text.strip(), link)
                        count += 1
        print(f"✅ 인크루트 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 인크루트 수집 실패: {e}")

def scrape_catch():
    try:
        url = "https://www.catch.co.kr/api/v1/recruit/list?page=1&pageSize=30"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            data = res.json()
            items = data.get('List', []) or data.get('list', [])
            for item in items:
                company = item.get('CompName', '') or item.get('companyName', '')
                title = item.get('Title', '') or item.get('title', '')
                full_title = f"[{company}] {title}" if company else title
                link = f"https://www.catch.co.kr/NCS/RecruitInfoDetail/{item.get('RecruitIdx', '')}"
                add_result('캐치', full_title, link)
                count += 1
        print(f"✅ 캐치 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 캐치 수집 실패: {e}")

def scrape_dokchisa():
    try:
        url = "https://cafe.naver.com/ArticleList.nhn?search.clubid=10986348&search.boardtype=L&search.totalCount=30&search.page=1"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for article in soup.select('div.article-board tr, table.board-box tr'):
                title_tag = article.select_one('a.article') or article.select_one('a.club')
                if title_tag:
                    add_result('독취사', title_tag.text.strip(), "https://cafe.naver.com" + title_tag.get('href', ''))
                    count += 1
        print(f"✅ 독취사 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 독취사 수집 실패: {e}")

def scrape_campung():
    try:
        url = "http://www.campung.com/board/list.asp?b_id=recruit"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('table.board_list tr') or soup.select('.list_box li'):
                title_tag = item.select_one('a')
                if title_tag:
                    href = title_tag.get('href', '')
                    link = f"http://www.campung.com/board/{href}" if not href.startswith('http') else href
                    add_result('아이캠펑', title_tag.text.strip(), link)
                    count += 1
        print(f"✅ 아이캠펑 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 아이캠펑 수집 실패: {e}")

def scrape_ssgsag():
    try:
        url = "https://api.ssgsag.kr/v1/feed/activities?page=1&size=30"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            data = res.json()
            items = data.get('content', []) or data.get('activities', []) or []
            for item in items:
                add_result('슥삭', item.get('title', ''), f"https://www.ssgsag.kr/activity/{item.get('id', '')}")
                count += 1
        print(f"✅ 슥삭 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 슥삭 수집 실패: {e}")

def scrape_campuspick():
    try:
        url = "https://api.campuspick.com/v1/activity/list?page=1"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            data = res.json()
            items = data.get('list', []) or data.get('activities', []) or []
            for item in items:
                add_result('캠퍼스픽', item.get('title', '') or item.get('name', ''), f"https://www.campuspick.com/activity/view?id={item.get('id', '')}")
                count += 1
        print(f"✅ 캠퍼스픽 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 캠퍼스픽 수집 실패: {e}")

def scrape_jobplanet():
    try:
        url = "https://www.jobplanet.co.kr/job/search?q=%ED%92%88%EC%A7%88"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('div.item_card') or soup.select('a.card_link'):
                title_tag = item.select_one('dt.title') or item.select_one('.jp_title')
                if title_tag:
                    link = item.get('href', '') if item.name == 'a' else item.select_one('a').get('href', '')
                    if link and not link.startswith('http'):
                        link = "https://www.jobplanet.co.kr" + link
                    add_result('잡플래닛', title_tag.text.strip(), link)
                    count += 1
        print(f"✅ 잡플래닛 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 잡플래닛 수집 실패: {e}")

def scrape_yw_work24():
    try:
        url = "https://yw.work24.go.kr/main.do"
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('.board_list tr, .program_list li, a'):
                text = item.text.strip()
                href = item.get('href', '') if item.name == 'a' else (item.select_one('a').get('href', '') if item.select_one('a') else '')
                if href and len(text) > 5:
                    link = "https://yw.work24.go.kr" + href if href.startswith('/') else href
                    add_result('미래내일일경험', text, link)
                    count += 1
        print(f"✅ 미래내일일경험 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 미래내일일경험 수집 실패: {e}")

def scrape_hyundai_hwgo():
    try:
        url = "https://hwgo.applyin.co.kr/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a, .notice_item'):
                text = item.text.strip()
                if len(text) > 5:
                    add_result('현대차 HereWeGo', text, url)
                    count += 1
        print(f"✅ 현대차 HereWeGo 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 현대차 HereWeGo 수집 실패: {e}")

def scrape_hmobility():
    try:
        url = "https://h-mobility-class.com/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a, .notice-item, .main-banner'):
                text = item.text.strip()
                if len(text) > 5:
                    add_result('현대차 H-mobility', text, url)
                    count += 1
        print(f"✅ 현대차 H-mobility 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 현대차 H-mobility 수집 실패: {e}")

def scrape_kmou_cts():
    try:
        url = "https://cts.kmou.ac.kr/ko/jobs/snotice"
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('table tr, .board_list li'):
                title_tag = item.select_one('a')
                date_tag = item.select_one('.date') or item.select_one('td.date')
                if title_tag:
                    title = title_tag.text.strip()
                    href = title_tag.get('href', '')
                    link = "https://cts.kmou.ac.kr" + href if href.startswith('/') else href
                    date = date_tag.text.strip() if date_tag else "-"
                    add_result('OCEAN-CTS(현장실습)', title, link, date)
                    count += 1
        print(f"✅ OCEAN-CTS 현장실습 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ OCEAN-CTS 현장실습 수집 실패: {e}")

def scrape_kmou_main():
    try:
        url = "https://www.kmou.ac.kr/kmou/na/ntt/selectNttList.do?mi=2032&bbsId=10373"
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('table.board-list tr, ul.board-list li'):
                title_tag = item.select_one('a') or item.select_one('.ntt-title')
                date_tag = item.select_one('td.date') or item.select_one('.date')
                if title_tag:
                    title = title_tag.text.strip()
                    href = title_tag.get('href', '')
                    link = "https://www.kmou.ac.kr/kmou/na/ntt/" + href if not href.startswith('http') else href
                    date = date_tag.text.strip() if date_tag else "-"
                    add_result('한국해양대 공지', title, link, date)
                    count += 1
        print(f"✅ 한국해양대 공지사항 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 한국해양대 공지사항 수집 실패: {e}")

def scrape_ksae():
    try:
        url = "https://www.ksae.org/index.php"
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('.notice_list li, .main_notice a, table.board tr'):
                text = item.text.strip()
                href = item.get('href', '') if item.name == 'a' else (item.select_one('a').get('href', '') if item.select_one('a') else '')
                if href and len(text) > 5:
                    link = "https://www.ksae.org/" + href if href.startswith('/') else href
                    add_result('한국자동차공학회', text, link)
                    count += 1
        print(f"✅ 한국자동차공학회 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 한국자동차공학회 수집 실패: {e}")

def scrape_ksoe():
    try:
        url = "http://www.ksoe.or.kr/"
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a, .notice li'):
                text = item.text.strip()
                href = item.get('href', '') if item.name == 'a' else ''
                if href and len(text) > 5:
                    link = "http://www.ksoe.or.kr/" + href if href.startswith('/') else href
                    add_result('한국해양공학회', text, link)
                    count += 1
        print(f"✅ 한국해양공학회 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 한국해양공학회 수집 실패: {e}")

def scrape_work24():
    try:
        url = "https://moelyouth.work24.go.kr/"
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a'):
                text = item.text.strip()
                href = item.get('href', '')
                if href and len(text) > 5:
                    add_result('고용24/청년', text, "https://moelyouth.work24.go.kr" + href if href.startswith('/') else href)
                    count += 1
        print(f"✅ 고용24/K-뉴딜 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 고용24/K-뉴딜 수집 실패: {e}")

def scrape_korcham_knda():
    try:
        url = "https://knda.korchamhrd.net/"
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a'):
                text = item.text.strip()
                href = item.get('href', '')
                if href and len(text) > 5:
                    add_result('대한상의 K-디지털', text, "https://knda.korchamhrd.net" + href if href.startswith('/') else href)
                    count += 1
        print(f"✅ 대한상의 K-디지털 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 대한상의 K-디지털 수집 실패: {e}")

def scrape_ps_korcham():
    try:
        url = "https://ps.korchamhrd.net/"
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a'):
                text = item.text.strip()
                href = item.get('href', '')
                if href and len(text) > 5:
                    add_result('부산인력개발원', text, "https://ps.korchamhrd.net" + href if href.startswith('/') else href)
                    count += 1
        print(f"✅ 부산인력개발원 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 부산인력개발원 수집 실패: {e}")

def scrape_winspec():
    try:
        url = "https://winspec.co.kr/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a'):
                text = item.text.strip()
                href = item.get('href', '')
                if href and len(text) > 5:
                    add_result('윈스펙', text, "https://winspec.co.kr" + href if href.startswith('/') else href)
                    count += 1
        print(f"✅ 윈스펙 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 윈스펙 수집 실패: {e}")

def scrape_comento():
    try:
        url = "https://comento.kr/job-questions"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a'):
                text = item.text.strip()
                href = item.get('href', '')
                if href and len(text) > 5:
                    add_result('코멘토', text, "https://comento.kr" + href if href.startswith('/') else href)
                    count += 1
        print(f"✅ 코멘토 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 코멘토 수집 실패: {e}")

def scrape_codeit_sprint():
    try:
        url = "https://sprint.codeit.kr/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select('a'):
                text = item.text.strip()
                href = item.get('href', '')
                if href and len(text) > 5:
                    add_result('코드잇스프린트', text, "https://sprint.codeit.kr" + href if href.startswith('/') else href)
                    count += 1
        print(f"✅ 코드잇스프린트 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 코드잇스프린트 수집 실패: {e}")

def scrape_jobkorea():
    try:
        count = 0
        search_keywords = ['품질', '생산관리', '부품구매', '현대모비스', 'HD현대']
        
        for kw in search_keywords:
            url = f"https://www.jobkorea.co.kr/Search/?stk={kw}"
            headers = HEADERS.copy()
            headers['Referer'] = 'https://www.jobkorea.co.kr/'
            
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select('article.list-item') or soup.select('li.list-post') or soup.select('.post-list-corp li')
                
                for item in items:
                    title_tag = item.select_one('a.title') or item.select_one('a.post-list-info') or item.select_one('.tit a')
                    corp_tag = item.select_one('a.name') or item.select_one('.corp-name a') or item.select_one('.coTit a')
                    
                    if title_tag:
                        title = title_tag.text.strip()
                        corp = corp_tag.text.strip() if corp_tag else ""
                        full_title = f"[{corp}] {title}" if corp else title
                        
                        href = title_tag.get('href', '')
                        if href:
                            link = "https://www.jobkorea.co.kr" + href if href.startswith('/') else href
                            add_result('잡코리아', full_title, link)
                            count += 1
                            
        print(f"✅ 잡코리아 수집 완료 (항목 수: {count})")
    except Exception as e:
        print(f"❌ 잡코리아 수집 실패: {e}")


# ---------------------------------------------------------
# [네이버 메일 발송]
# ---------------------------------------------------------
def send_naver_email(html_content, total_count):
    naver_user = os.getenv("NAVER_USER")
    naver_password = os.getenv("NAVER_PASSWORD")
    
    if not naver_user or not naver_password:
        print("⚠️ NAVER_USER 또는 NAVER_PASSWORD 환경변수가 없습니다. 메일 발송을 스킵합니다.")
        return

    sender_email = naver_user if "@naver.com" in naver_user else f"{naver_user}@naver.com"
    receiver_email = sender_email

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    subject = f"[맞춤 공고 알림] {today_str} 통합 공고/지원사업 리스트 ({total_count}건)"

    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.naver.com", 465) as server:
            server.login(naver_user.split('@')[0], naver_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("✉️ 네이버 메일 발송 완료!")
    except Exception as e:
        print(f"❌ 메일 발송 실패: {e}")

# ---------------------------------------------------------
# [메인 실행부]
# ---------------------------------------------------------
if __name__ == "__main__":
    print("🚀 전체 수집 대상 사이트 스크래핑을 시작합니다...")
    
    # 1차 채용 사이트
    scrape_linkareer()
    scrape_jasoseol()
    scrape_incruit()
    scrape_catch()
    scrape_dokchisa()
    scrape_campung()
    scrape_ssgsag()
    scrape_campuspick()
    scrape_jobplanet()
    scrape_jobkorea()

    # 2차 추가 사이트 (대학, 현대차, 공학회, 지원사업)
    scrape_yw_work24()
    scrape_hyundai_hwgo()
    scrape_hmobility()
    scrape_kmou_cts()
    scrape_kmou_main()
    scrape_ksae()
    scrape_ksoe()
    scrape_work24()
    scrape_korcham_knda()
    scrape_ps_korcham()
    scrape_winspec()
    scrape_comento()
    scrape_codeit_sprint()

    today = datetime.date.today().strftime('%Y년 %m월 %d일')
    
    if results:
        df = pd.DataFrame(results).drop_duplicates(subset=['제목']).reset_index(drop=True)
        df.to_csv('latest_jobs.csv', index=False, encoding='utf-8-sig')
        
        md_text = f"# 📢 오늘의 맞춤 관심 공고 ({today})\n\n"
        md_text += "| 출처 | 제목 | 링크 | 마감/등록일 |\n"
        md_text += "| :--- | :--- | :--- | :--- |\n"
        
        html_text = f"<h2>📢 오늘의 맞춤 관심 공고 목록 ({today}) - 총 {len(df)}건</h2>"
        html_text += "<table border='1' style='border-collapse: collapse; padding: 8px;'><tr bgcolor='#f2f2f2'><th>출처</th><th>제목</th><th>마감/등록일</th></tr>"
        
        for _, row in df.iterrows():
            md_text += f"| {row['출처']} | {row['제목']} | [바로가기]({row['링크']}) | {row['등록일']} |\n"
            html_text += f"<tr><td><b>{row['출처']}</b></td><td><a href='{row['링크']}'>{row['제목']}</a></td><td>{row['등록일']}</td></tr>"
            
        html_text += "</table>"
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(md_text)
            
        send_naver_email(html_text, len(df))
        print(f"✅ 총 {len(df)}건의 맞춤 공고 수집 완료!")
    else:
        print("조건에 알맞은 신규 공고가 없습니다.")
        html_text = f"<h2>📢 {today} 스크래퍼 실행 결과</h2><p>오늘 설정한 키워드에 부합하는 신규 공고가 발견되지 않았습니다.</p>"
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(f"# 📢 오늘의 주요 공고 ({today})\n\n오늘 조건에 알맞은 공고가 없습니다.")
        send_naver_email(html_text, 0)
