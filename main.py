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
# 1. 링커리어 (Linkareer)
# ---------------------------------------------------------
def scrape_linkareer():
    try:
        url = "https://api.linkareer.com/api/v1/activity/list?page=1&perPage=30&sort=CREATED_AT_DESC"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get('data', {}).get('activities', {}).get('nodes', [])
            for item in items:
                title = item.get('title', '')
                act_id = item.get('id', '')
                link = f"https://linkareer.com/activity/{act_id}"
                add_result('링커리어', title, link)
            print(f"✅ 링커리어 수집 진행 완료 (검색된 항목 수: {len(items)})")
    except Exception as e:
        print(f"❌ 링커리어 수집 실패: {e}")

# ---------------------------------------------------------
# 2. 자소설닷컴 (Jasoseol)
# ---------------------------------------------------------
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
                emp_id = item.get('id', '')
                
                full_title = f"[{company}] {title}" if company else title
                link = f"https://jasoseol.com/recruit/{emp_id}"
                
                end_date = item.get('end_date', '-')
                if end_date and len(str(end_date)) >= 10:
                    end_date = str(end_date)[:10]
                    
                add_result('자소설닷컴', full_title, link, end_date)
            print(f"✅ 자소설닷컴 수집 진행 완료 (검색된 항목 수: {len(employments)})")
    except Exception as e:
        print(f"❌ 자소설닷컴 수집 실패: {e}")

# ---------------------------------------------------------
# 3. 인크루트 (Incruit)
# ---------------------------------------------------------
def scrape_incruit():
    try:
        count = 0
        for kw in ['인턴', '품질', '채용']:
            url = f"https://search.incruit.com/list/search.asp?kw={kw}"
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select('div.n_job_list_table ul > li')
                for item in items:
                    title_tag = item.select_one('a.title') or item.select_one('span.cell_mid a')
                    if title_tag:
                        title = title_tag.text.strip()
                        link = title_tag.get('href', '')
                        if not link.startswith('http'):
                            link = 'https:' + link if link.startswith('//') else 'https://job.incruit.com' + link
                        add_result('인크루트', title, link)
                        count += 1
        print(f"✅ 인크루트 수집 진행 완료 (검색된 항목 수: {count})")
    except Exception as e:
        print(f"❌ 인크루트 수집 실패: {e}")

# ---------------------------------------------------------
# 4. 캐치 (Catch)
# ---------------------------------------------------------
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
                rec_id = item.get('RecruitIdx', '') or item.get('recruitIdx', '')
                full_title = f"[{company}] {title}" if company else title
                link = f"https://www.catch.co.kr/NCS/RecruitInfoDetail/{rec_id}"
                add_result('캐치', full_title, link)
                count += 1
        else:
            # HTML 파싱 폴백
            fallback_url = "https://www.catch.co.kr/NCS/Recruit"
            res = requests.get(fallback_url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select('table.tbl_type1 tbody tr')
                for item in items:
                    title_tag = item.select_one('td.al a')
                    if title_tag:
                        title = title_tag.text.strip()
                        link = "https://www.catch.co.kr" + title_tag.get('href', '')
                        add_result('캐치', title, link)
                        count += 1
        print(f"✅ 캐치 수집 진행 완료 (검색된 항목 수: {count})")
    except Exception as e:
        print(f"❌ 캐치 수집 실패: {e}")

# ---------------------------------------------------------
# 5. 독취사 (네이버 카페)
# ---------------------------------------------------------
def scrape_dokchisa():
    try:
        # 독취사 카페 주요 공고/게시판 iframe URL
        club_id = "10986348"
        url = f"https://cafe.naver.com/ArticleList.nhn?search.clubid={club_id}&search.boardtype=L&search.totalCount=30&search.page=1"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.select('div.article-board tr, table.board-box tr')
            for article in articles:
                title_tag = article.select_one('a.article') or article.select_one('a.club')
                if title_tag:
                    title = title_tag.text.strip()
                    link = "https://cafe.naver.com" + title_tag.get('href', '')
                    add_result('독취사', title, link)
                    count += 1
        print(f"✅ 독취사 수집 진행 완료 (검색된 항목 수: {count})")
    except Exception as e:
        print(f"❌ 독취사 수집 실패: {e}")

# ---------------------------------------------------------
# 6. 아이캠펑 (Campung)
# ---------------------------------------------------------
def scrape_campung():
    try:
        url = "http://www.campung.com/board/list.asp?b_id=recruit"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select('table.board_list tr') or soup.select('.list_box li')
            for item in items:
                title_tag = item.select_one('a')
                if title_tag:
                    title = title_tag.text.strip()
                    href = title_tag.get('href', '')
                    link = f"http://www.campung.com/board/{href}" if not href.startswith('http') else href
                    add_result('아이캠펑', title, link)
                    count += 1
        print(f"✅ 아이캠펑 수집 진행 완료 (검색된 항목 수: {count})")
    except Exception as e:
        print(f"❌ 아이캠펑 수집 실패: {e}")

# ---------------------------------------------------------
# 7. 슥삭 (SSGSAG)
# ---------------------------------------------------------
def scrape_ssgsag():
    try:
        url = "https://api.ssgsag.kr/v1/feed/activities?page=1&size=30"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            data = res.json()
            items = data.get('content', []) or data.get('activities', []) or []
            for item in items:
                title = item.get('title', '')
                act_id = item.get('id', '')
                link = f"https://www.ssgsag.kr/activity/{act_id}"
                add_result('슥삭', title, link)
                count += 1
        print(f"✅ 슥삭 수집 진행 완료 (검색된 항목 수: {count})")
    except Exception as e:
        print(f"❌ 슥삭 수집 실패: {e}")

# ---------------------------------------------------------
# 8. 캠퍼스픽 (Campuspick)
# ---------------------------------------------------------
def scrape_campuspick():
    try:
        url = "https://api.campuspick.com/v1/activity/list?page=1"
        res = requests.get(url, headers=HEADERS, timeout=10)
        count = 0
        if res.status_code == 200:
            data = res.json()
            items = data.get('list', []) or data.get('activities', []) or []
            for item in items:
                title = item.get('title', '') or item.get('name', '')
                act_id = item.get('id', '')
                link = f"https://www.campuspick.com/activity/view?id={act_id}"
                add_result('캠퍼스픽', title, link)
                count += 1
        print(f"✅ 캠퍼스픽 수집 진행 완료 (검색된 항목 수: {count})")
    except Exception as e:
        print(f"❌ 캠퍼스픽 수집 실패: {e}")

# ---------------------------------------------------------
# 9. 잡플래닛 (Jobplanet)
# ---------------------------------------------------------
def scrape_jobplanet():
    try:
        url = "https://www.jobplanet.co.kr/job/search?q=%ED%92%88%EC%A7%88"
        headers = HEADERS.copy()
        headers['Accept-Language'] = 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        res = requests.get(url, headers=headers, timeout=10)
        count = 0
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select('div.item_card') or soup.select('a.card_link')
            for item in items:
                title_tag = item.select_one('dt.title') or item.select_one('.jp_title')
                if title_tag:
                    title = title_tag.text.strip()
                    link = item.get('href', '') if item.name == 'a' else item.select_one('a').get('href', '')
                    if link and not link.startswith('http'):
                        link = "https://www.jobplanet.co.kr" + link
                    add_result('잡플래닛', title, link)
                    count += 1
        print(f"✅ 잡플래닛 수집 진행 완료 (검색된 항목 수: {count})")
    except Exception as e:
        print(f"❌ 잡플래닛 수집 실패: {e}")

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
    subject = f"[맞춤 공고 알림] {today_str} 주요 채용 및 대외활동 공고 ({total_count}건)"

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
    print("🚀 주요 사이트 공고 통합 스크래핑을 시작합니다...")
    
    # 총 9개 사이트 스크래퍼 실행
    scrape_linkareer()
    scrape_jasoseol()
    scrape_incruit()
    scrape_catch()
    scrape_dokchisa()
    scrape_campung()
    scrape_ssgsag()
    scrape_campuspick()
    scrape_jobplanet()

    today = datetime.date.today().strftime('%Y년 %m월 %d일')
    
    if results:
        df = pd.DataFrame(results).drop_duplicates(subset=['제목']).reset_index(drop=True)
        df.to_csv('latest_jobs.csv', index=False, encoding='utf-8-sig')
        
        md_text = f"# 📢 오늘의 주요 관심 공고 ({today})\n\n"
        md_text += "| 출처 | 제목 | 링크 | 마감/등록일 |\n"
        md_text += "| :--- | :--- | :--- | :--- |\n"
        
        html_text = f"<h2>📢 오늘의 관심 공고 목록 ({today}) - 총 {len(df)}건</h2>"
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
