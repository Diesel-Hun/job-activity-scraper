import os
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import pandas as pd

# 관심 키워드
KEYWORDS = ['자동차', '조선', '재료', '배터리', '품질', '자율주행', '현장실습', '인턴', '공모전']

results = []

def add_result(source, title, link, date="-"):
    if any(keyword in title for keyword in KEYWORDS):
        results.append({
            '출처': source,
            '제목': title.strip(),
            '링크': link,
            '등록일': date
        })

def search_kmou_notice():
    print("▶ 한국해양대학교 공지사항 수집 중...")
    url = "https://www.kmou.ac.kr/kmou/na/ntt/selectNttList.do?mi=2032&bbsId=10373"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('table.tbl tbody tr')
        for row in rows:
            title_tag = row.select_one('td.nttInfoSubject a')
            date_tag = row.select_one('td:nth-child(5)')
            if title_tag:
                title = title_tag.text.strip()
                href = title_tag.get('href', '')
                link = f"https://www.kmou.ac.kr/kmou/na/ntt/selectNttInfo.do{href}" if href.startswith('?') or 'selectNttInfo' in href else url
                date = date_tag.text.strip() if date_tag else "-"
                add_result('한국해양대 공지', title, link, date)
    except Exception as e:
        print(f"❌ 한국해양대 오류: {e}")

def search_kmou_cts():
    print("▶ Ocean-CTS 현장실습 수집 중...")
    url = "https://cts.kmou.ac.kr/ko/jobs/snotice"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('table tbody tr') or soup.select('.board-list li')
        for item in items:
            a_tag = item.select_one('a')
            if a_tag:
                title = a_tag.text.strip()
                link = a_tag.get('href', '')
                if not link.startswith('http'):
                    link = "https://cts.kmou.ac.kr" + link
                add_result('Ocean-CTS 현장실습', title, link)
    except Exception as e:
        print(f"❌ Ocean-CTS 오류: {e}")

def search_ksae():
    print("▶ 한국자동차공학회 수집 중...")
    url = "https://www.ksae.org/notice/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a_tag in soup.select('a'):
            title = a_tag.text.strip()
            href = a_tag.get('href', '')
            if len(title) > 5 and ('board' in href or 'notice' in href):
                if not href.startswith('http'):
                    href = "https://www.ksae.org" + href
                add_result('한국자동차공학회', title, href)
    except Exception as e:
        print(f"❌ 한국자동차공학회 오류: {e}")

def send_naver_email(html_content, total_count):
    naver_user = os.getenv("NAVER_USER")
    naver_password = os.getenv("NAVER_PASSWORD")
    
    if not naver_user or not naver_password:
        print("❌ NAVER_USER 또는 NAVER_PASSWORD 환경변수가 없습니다.")
        return

    # 아이디에 @naver.com이 포함 안 되어 있을 경우 붙여줌
    sender_email = naver_user if "@naver.com" in naver_user else f"{naver_user}@naver.com"
    receiver_email = sender_email

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    subject = f"[아침 알림] {today_str} 자동차·조선·재료 공고 ({total_count}건)"

    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.naver.com", 465) as server:
            server.login(naver_user.split('@')[0], naver_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("✉️ 네이버 메일 발송 성공!")
    except Exception as e:
        print(f"❌ 메일 발송 실패: {e}")

if __name__ == "__main__":
    search_kmou_notice()
    search_kmou_cts()
    search_ksae()
    
    if results:
        df = pd.DataFrame(results).drop_duplicates(subset=['제목']).reset_index(drop=True)
        df.to_csv('latest_jobs.csv', index=False, encoding='utf-8-sig')
        
        today = datetime.date.today().strftime('%Y년 %m월 %d일')
        
        # README.md 작성용
        md_text = f"# 🚗⚓ 오늘의 공고 알림 ({today})\n\n| 출처 | 제목 | 링크 | 등록일 |\n| :--- | :--- | :--- | :--- |\n"
        # 메일 수신용 HTML
        html_text = f"<h2>📢 오늘의 자동차·조선·재료 공고 ({today})</h2><table border='1' style='border-collapse: collapse; padding: 8px;'><tr bgcolor='#f2f2f2'><th>출처</th><th>제목</th><th>등록일</th></tr>"
        
        for _, row in df.iterrows():
            md_text += f"| {row['출처']} | {row['제목']} | [바로가기]({row['링크']}) | {row['등록일']} |\n"
            html_text += f"<tr><td>{row['출처']}</td><td><a href='{row['링크']}'>{row['제목']}</a></td><td>{row['등록일']}</td></tr>"
            
        html_text += "</table>"
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(md_text)
            
        send_naver_email(html_text, len(df))
    else:
        print("조건에 맞는 공고가 없습니다.")
