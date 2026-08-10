import os
import datetime
import smtplib
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
    '현장실습', '인턴', '공모전', '대외활동', '교육', '부트캠프', '일경험'
]

# 결과 저장 리스트
results = []

def add_result(source, title, link, date="-"):
    """키워드 검사 후 결과 리스트에 추가"""
    if not title or not isinstance(title, str):
        return
    title_clean = title.strip()
    if any(keyword in title_clean for keyword in KEYWORDS):
        results.append({
            '출처': source,
            '제목': title_clean,
            '링크': link,
            '등록일': date
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
                title = title_tag.text.strip()
                href = title_tag.get('href', '')
                link = f"https://www.kmou.ac.kr/kmou/na/ntt/selectNttInfo.do{href}" if href.startswith('?') else url
                date = date_tag.text.strip() if date_tag else "-"
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
            title = a_tag.text.strip()
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
            title = a.text.strip()
            href = a.get('href', '')
            if len(title) > 5 and ('board' in href or 'notice' in href):
                link = f"https://www.ksae.org{href}" if href.startswith('/') else href
                add_result('한국자동차공학회', title, link)
    except Exception as e:
        print(f"❌ 한국자동차공학회 수집 실패: {e}")

def scrape_ksoe():
    """4. 한국해양공학회"""
    try:
        url = "http://www.ksoe.or.kr/"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('a'):
            title = a.text.strip()
            href = a.get('href', '')
            if len(title) > 5:
                link = f"http://www.ksoe.or.kr/{href}" if href.startswith('?') else href
                add_result('한국해양공학회', title, link)
    except Exception as e:
        print(f"❌ 한국해양공학회 수집 실패: {e}")

def scrape_korcham_knda():
    """5. 대한상공회의소 K-디지털 혁신인재 / 부산인력개발원"""
    sites = [
        ('대한상의 K-디지털', 'https://knda.korchamhrd.net/'),
        ('부산인력개발원', 'https://ps.korchamhrd.net/')
    ]
    for name, url in sites:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.select('a'):
                title = a.text.strip()
                href = a.get('href', '')
                if len(title) > 6:
                    add_result(name, title, url)
        except Exception as e:
            print(f"❌ {name} 수집 실패: {e}")

def scrape_linkareer():
    """6. 링커리어 (공모전/대외활동 API)"""
    try:
        url = "https://api.linkareer.com/api/v1/activity/list?page=1&perPage=20&sort=CREATED_AT_DESC"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
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
    """7. 윈스펙 (직무교육/인턴십)"""
    try:
        url = "https://winspec.co.kr/"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('a'):
            title = a.text.strip()
            href = a.get('href', '')
            if len(title) > 6:
                link = f"https://winspec.co.kr{href}" if href.startswith('/') else href
                add_result('윈스펙', title, link)
    except Exception as e:
        print(f"❌ 윈스펙 수집 실패: {e}")

def scrape_ssgsag():
    """8. 슥삭 (SSGSAG)"""
    try:
        url = "https://www.ssgsag.kr/"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.select('a'):
            title = a.text.strip()
            href = a.get('href', '')
            if len(title) > 5:
                link = f"https://www.ssgsag.kr{href}" if href.startswith('/') else href
                add_result('슥삭', title, link)
    except Exception as e:
        print(f"❌ 슥삭 수집 실패: {e}")

def scrape_work24():
    """9. 고용24 / 청년일경험 / K-뉴딜 아카데미"""
    urls = [
        ('고용24', 'https://www.work24.go.kr/cm/main.do'),
        ('미래내일 일경험', 'https://yw.work24.go.kr/main.do'),
        ('K-뉴딜 아카데미', 'https://moelyouth.work24.go.kr/')
    ]
    for name, url in urls:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.select('a'):
                title = a.text.strip()
                if len(title) > 6:
                    add_result(name, title, url)
        except Exception as e:
            print(f"❌ {name} 수집 실패: {e}")

def scrape_hyundai_programs():
    """10. 현대자동차 Here we go / H-Mobility Class"""
    programs = [
        ('현대차 Here We Go', 'https://hwgo.applyin.co.kr/'),
        ('현대차 H-Mobility Class', 'https://h-mobility-class.com/')
    ]
    for name, url in programs:
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text()
            # 주요 모빌리티 키워드 포함 여부 직접 확인
            for kw in ['수강생', '모집', '차량', '자율주행', '전동화', '배터리', '공고']:
                if kw in text:
                    add_result(name, f"[{name}] 신규 모집/공지사항 업데이트 확인 필요", url)
                    break
        except Exception as e:
            print(f"❌ {name} 수집 실패: {e}")

def scrape_job_platforms():
    """11. 잡코리아, 인크루트, 캐치, 자소설닷컴, 잡플래닛, 코멘토, 아이캠펑, 캠퍼스픽, 코드잇"""
    platforms = [
        ('잡코리아', 'https://www.jobkorea.co.kr/'),
        ('인크루트', 'https://www.incruit.com/'),
        ('캐치', 'https://www.catch.co.kr/'),
        ('자소설닷컴', 'https://jasoseol.com/'),
        ('잡플래닛', 'https://www.jobplanet.co.kr/'),
        ('코멘토', 'https://comento.kr/'),
        ('아이캠펑', 'http://www.campung.com/'),
        ('캠퍼스픽', 'https://www.campuspick.com/'),
        ('코드잇 스프린트', 'https://sprint.codeit.kr/')
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    for name, url in platforms:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            soup = BeautifulSoup(res.text, 'html.parser')
            for a in soup.select('a'):
                title = a.text.strip()
                href = a.get('href', '')
                if len(title) > 5 and any(k in title for k in KEYWORDS):
                    link = href if href.startswith('http') else f"{url.rstrip('/')}/{href.lstrip('/')}"
                    add_result(name, title, link)
        except Exception as e:
            print(f"⚠️ {name} 보안 차단 또는 접속 제한 (크롤링 방지 적용됨)")

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
    scrape_ssgsag()
    scrape_work24()
    scrape_hyundai_programs()
    scrape_job_platforms()

    today = datetime.date.today().strftime('%Y년 %m월 %d일')
    
    if results:
        df = pd.DataFrame(results).drop_duplicates(subset=['제목']).reset_index(drop=True)
        df.to_csv('latest_jobs.csv', index=False, encoding='utf-8-sig')
        
        md_text = f"# 🚗⚓ 오늘의 자동차·조선·재료 공고 ({today})\n\n| 출처 | 제목 | 링크 | 등록일 |\n| :--- | :--- | :--- | :--- |\n"
        html_text = f"<h2>📢 오늘의 관심 공고 목록 ({today}) - 총 {len(df)}건</h2><table border='1' style='border-collapse: collapse; padding: 8px;'><tr bgcolor='#f2f2f2'><th>출처</th><th>제목</th><th>등록일</th></tr>"
        
        for _, row in df.iterrows():
            md_text += f"| {row['출처']} | {row['제목']} | [바로가기]({row['링크']}) | {row['등록일']} |\n"
            html_text += f"<tr><td><b>{row['출처']}</b></td><td><a href='{row['링크']}'>{row['제목']}</a></td><td>{row['등록일']}</td></tr>"
            
        html_text += "</table>"
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(md_text)
            
        send_naver_email(html_text, len(df))
    else:
        print("조건에 알맞은 신규 공고가 없습니다. 안내 메일을 전송합니다.")
        html_text = f"<h2>📢 {today} 통합 스크래퍼 실행 결과</h2><p>오늘 설정한 키워드(자동차, 조선, 재료, 현장실습, 인턴 등)에 부합하는 신규 공고가 발견되지 않았습니다.</p>"
        send_naver_email(html_text, 0)
