import os
import datetime
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ---------------------------------------------------------
# [설정] 수집 대상 키워드 목록
# ---------------------------------------------------------
KEYWORDS = [
    '자동차', '조선', '재료', '금속', '배터리', '품질', '자율주행', 
    '현장실습', '인턴', '공모전', '대외활동', '교육', '부트캠프', '일경험',
    '채용', '모집', '안내', '사업', '과정', '아카데미', 'K-디지털', 'SW'
]

# 결과 저장 리스트
results = []

def clean_text(text):
    """마크다운 표 깨짐 방지를 위한 텍스트 정제 함수"""
    if not text:
        return ""
    # 파이프(|) 기호를 HTML 엔티티로 변경
    text = text.replace('|', '&#124;')
    # 줄바꿈 및 연속 공백 정리
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def add_result(source, title, link, date="-"):
    """키워드 검사 후 결과 리스트에 추가"""
    if not title or not isinstance(title, str):
        return
    
    title_clean = clean_text(title)
    if len(title_clean) < 3:
        return

    # 키워드 일치 확인 (단순 포함 여부)
    if any(keyword in title_clean for keyword in KEYWORDS):
        results.append({
            '출처': clean_text(source),
            '제목': title_clean,
            '링크': link.strip(),
            '등록일': clean_text(date)
        })

# ---------------------------------------------------------
# [크롤러 모듈] 사이트별 수집 로직
# ---------------------------------------------------------

def scrape_kmou():
    """1. 한국해양대학교 공지사항"""
    try:
        url = "https://www.kmou.ac.kr/kmou/na/ntt/selectNttList.do?mi=2032&bbsId=10373"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for row in soup.select('table.tbl tbody tr'):
            title_tag = row.select_one('td.nttInfoSubject a')
            date_tag = row.select_one('td:nth-child(5)')
            if title_tag:
                title = title_tag.text
                href = title_tag.get('href', '')
                link = f"https://www.kmou.ac.kr/kmou/na/ntt/selectNttInfo.do{href}" if href.startswith('?') else url
                date = date_tag.text if date_tag else "-"
                add_result('한국해양대 공지', title, link, date)
    except Exception as e:
        print(f"❌ 한국해양대 수집 실패: {e}")

def scrape_ocean_cts():
    """2. Ocean-CTS (현장실습)"""
    try:
        url = "https://cts.kmou.ac.kr/ko/jobs/snotice"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a_tag in soup.select('table tbody tr a, .board-list a'):
            title = a_tag.text
            href = a_tag.get('href', '')
            link = f"https://cts.kmou.ac.kr{href}" if href.startswith('/') else href
            add_result('Ocean-CTS 현장실습', title, link)
    except Exception as e:
        print(f"❌ Ocean-CTS 수집 실패: {e}")

def scrape_ksae():
    """3. 한국자동차공학회"""
    try:
        url = "https://www.ksae.org/notice/"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('a'):
            title = a.text
            href = a.get('href', '')
            if len(title.strip()) > 5:
                link = f"https://www.ksae.org{href}" if href.startswith('/') else href
                add_result('한국자동차공학회', title, link)
    except Exception as e:
        print(f"❌ 한국자동차공학회 수집 실패: {e}")

def scrape_ksoe():
    """4. 한국해양공학회"""
    try:
        url = "http://www.ksoe.or.kr/bbs/list.php?code=notice"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('a'):
            title = a.text
            href = a.get('href', '')
            if len(title.strip()) > 5:
                link = f"http://www.ksoe.or.kr/{href}" if href.startswith('?') or href.startswith('bbs') else href
                add_result('한국해양공학회', title, link)
    except Exception as e:
        print(f"❌ 한국해양공학회 수집 실패: {e}")

def scrape_korcham_knda():
    """5. 대한상공회의소 / 부산인력개발원"""
    sites = [
        ('대한상의 K-디지털', 'https://knda.korchamhrd.net/'),
        ('부산인력개발원', 'https://ps.korchamhrd.net/')
    ]
    for name, url in sites:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.select('a'):
                title = a.text
                href = a.get('href', '')
                if len(title.strip()) > 5:
                    link = f"{url.rstrip('/')}/{href.lstrip('/')}" if not href.startswith('http') else href
                    add_result(name, title, link)
        except Exception as e:
            print(f"❌ {name} 수집 실패: {e}")

def scrape_linkareer():
    """6. 링커리어 API"""
    try:
        url = "https://api.linkareer.com/api/v1/activity/list?page=1&perPage=20&sort=CREATED_AT_DESC"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get('data', {}).get('activities', {}).get('nodes', [])
            for item in items:
                title = item.get('title', '')
                act_id = item.get('id', '')
                link = f"https://linkareer.com/activity/{act_id}"
                add_result('링커리어', title, link)
    except Exception as e:
        print(f"❌ 링커리어 수집 실패: {e}")

def scrape_winspec():
    """7. 윈스펙"""
    try:
        url = "https://winspec.co.kr/"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('a'):
            title = a.text
            href = a.get('href', '')
            if len(title.strip()) > 5:
                link = f"https://winspec.co.kr{href}" if href.startswith('/') else href
                add_result('윈스펙', title, link)
    except Exception as e:
        print(f"❌ 윈스펙 수집 실패: {e}")

def scrape_hyundai_programs():
    """8. 현대자동차 모빌리티 공고"""
    programs = [
        ('현대차 Here We Go', 'https://hwgo.applyin.co.kr/'),
        ('현대차 H-Mobility Class', 'https://h-mobility-class.com/')
    ]
    for name, url in programs:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text()
            for kw in ['수강생', '모집', '차량', '자율주행', '전동화', '배터리', '공고', '인턴']:
                if kw in text:
                    add_result(name, f"[{name}] 모집 및 프로그램 안내 확인하기", url)
                    break
        except Exception as e:
            print(f"❌ {name} 수집 실패: {e}")

# ---------------------------------------------------------
# [메일 발송 모듈]
# ---------------------------------------------------------
def send_naver_email(html_content, total_count):
    naver_user = os.getenv("NAVER_USER")
    naver_password = os.getenv("NAVER_PASSWORD")
    
    if not naver_user or not naver_password:
        print("❌ NAVER_USER 또는 NAVER_PASSWORD 환경변수가 없습니다.")
        return

    sender_email = naver_user if "@naver.com" in naver_user else f"{naver_user}@naver.com"
    receiver_email = sender_email

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    subject = f"[통합 공고 알림] {today_str} 자동차/조선/재료 맞춤 공고 ({total_count}건)"

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
    print("🚀 전체 사이트 대상 공고 스크래핑을 시작합니다...")
    
    scrape_kmou()
    scrape_ocean_cts()
    scrape_ksae()
    scrape_ksoe()
    scrape_korcham_knda()
    scrape_linkareer()
    scrape_winspec()
    scrape_hyundai_programs()

    today = datetime.date.today().strftime('%Y년 %m월 %d일')
    
    if results:
        df = pd.DataFrame(results).drop_duplicates(subset=['제목']).reset_index(drop=True)
        df.to_csv('latest_jobs.csv', index=False, encoding='utf-8-sig')
        
        # README 마크다운 작성 (줄바꿈 엄격 적용)
        md_text = f"# 🚗⚓ 오늘의 자동차·조선·재료 공고 ({today})\n\n"
        md_text += "| 출처 | 제목 | 링크 | 등록일 |\n"
        md_text += "| :--- | :--- | :--- | :--- |\n"
        
        html_text = f"<h2>📢 오늘의 관심 공고 목록 ({today}) - 총 {len(df)}건</h2>"
        html_text += "<table border='1' style='border-collapse: collapse; padding: 8px;'><tr bgcolor='#f2f2f2'><th>출처</th><th>제목</th><th>등록일</th></tr>"
        
        for _, row in df.iterrows():
            md_text += f"| {row['출처']} | {row['제목']} | [바로가기]({row['링크']}) | {row['등록일']} |\n"
            html_text += f"<tr><td><b>{row['출처']}</b></td><td><a href='{row['링크']}'>{row['제목']}</a></td><td>{row['등록일']}</td></tr>"
            
        html_text += "</table>"
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(md_text)
            
        send_naver_email(html_text, len(df))
        print(f"✅ 총 {len(df)}건의 공고 수집 및 업데이트 성공!")
    else:
        print("조건에 알맞은 신규 공고가 없습니다. 안내 메일을 전송합니다.")
        html_text = f"<h2>📢 {today} 통합 스크래퍼 실행 결과</h2><p>오늘 설정한 키워드에 부합하는 신규 공고가 발견되지 않았습니다.</p>"
        send_naver_email(html_text, 0)
