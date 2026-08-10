import os
import datetime
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
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
# 1. 링커리어 (Linkareer) 크롤러
# ---------------------------------------------------------
def scrape_linkareer():
    try:
        url = "https://api.linkareer.com/api/v1/activity/list?page=1&perPage=30&sort=CREATED_AT_DESC"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=10)
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
# 2. 자소설닷컴 (Jasoseol) 크롤러
# ---------------------------------------------------------
def scrape_jasoseol():
    try:
        # 자소설닷컴 실시간 공고 목록 API
        url = "https://jasoseol.com/api/v1/employment/list"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://jasoseol.com/'
        }
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
                
                # 마감일 정보가 있는 경우
                end_date = item.get('end_date', '-')
                if end_date and len(str(end_date)) >= 10:
                    end_date = str(end_date)[:10]
                    
                add_result('자소설닷컴', full_title, link, end_date)
            print(f"✅ 자소설닷컴 수집 진행 완료 (검색된 항목 수: {len(employments)})")
    except Exception as e:
        print(f"❌ 자소설닷컴 수집 실패: {e}")

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
    subject = f"[맞춤 공고 알림] {today_str} 링커리어 & 자소설닷컴 주요 공고 ({total_count}건)"

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
    print("🚀 링커리어 & 자소설닷컴 공고 스크래핑을 시작합니다...")
    
    scrape_linkareer()
    scrape_jasoseol()

    today = datetime.date.today().strftime('%Y년 %m월 %d일')
    
    if results:
        df = pd.DataFrame(results).drop_duplicates(subset=['제목']).reset_index(drop=True)
        df.to_csv('latest_jobs.csv', index=False, encoding='utf-8-sig')
        
        md_text = f"# 📢 오늘의 링커리어 & 자소설닷컴 주요 공고 ({today})\n\n"
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
