import os
import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd

# ==========================================
# 1. 관심 키워드 및 수집 결과 저장소
# ==========================================
KEYWORDS = ['자동차', '조선', '재료', '배터리', '품질', '자율주행', '현장실습', '인턴', '공모전']

results = []

def add_result(source, title, link, date="-"):
    """수집된 결과를 공통 양식으로 저장하는 함수"""
    # 키워드가 제목에 포함되어 있는지 검사
    if any(keyword in title for keyword in KEYWORDS):
        # 중복 방지를 위해 리스트 추가
        results.append({
            '출처': source,
            '제목': title.strip(),
            '링크': link,
            '등록일': date
        })

# ==========================================
# 2. 사이트별 크롤러 함수
# ==========================================

def search_kmou_notice():
    """1) 한국해양대학교 일반공지 수집"""
    print("▶ 한국해양대학교 공지사항 수집 중...")
    url = "https://www.kmou.ac.kr/kmou/na/ntt/selectNttList.do?mi=2032&bbsId=10373"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 게시글 목록 추출
        rows = soup.select('table.tbl tbody tr')
        for row in rows:
            title_tag = row.select_one('td.nttInfoSubject a')
            date_tag = row.select_one('td:nth-child(5)') # 날짜 컬럼
            
            if title_tag:
                title = title_tag.text.strip()
                # 상대 경로 링크를 절대 경로로 변환
                href = title_tag.get('href', '')
                link = f"https://www.kmou.ac.kr/kmou/na/ntt/selectNttInfo.do{href}" if href.startswith('?') or 'selectNttInfo' in href else url
                date = date_tag.text.strip() if date_tag else "-"
                
                add_result('한국해양대 공지', title, link, date)
    except Exception as e:
        print(f"❌ 한국해양대 수집 중 오류: {e}")

def search_kmou_cts():
    """2) 한국해양대학교 Ocean-CTS 현장실습 공지 수집"""
    print("▶ Ocean-CTS 현장실습 공지 수집 중...")
    url = "https://cts.kmou.ac.kr/ko/jobs/snotice"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 글 목록 항목 찾기
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
        print(f"❌ Ocean-CTS 수집 중 오류: {e}")

def search_ksae():
    """3) 한국자동차공학회 공지사항/행사 수집"""
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
        print(f"❌ 한국자동차공학회 수집 중 오류: {e}")

# ==========================================
# 3. 메인 실행 및 결과 리포트(README.md) 저장
# ==========================================
if __name__ == "__main__":
    print("🚀 공고 및 대외활동 자동 수집을 시작합니다...")
    
    # 각각의 수집 함수 실행
    search_kmou_notice()
    search_kmou_cts()
    search_ksae()
    
    # 수집 결과 정리 및 저장
    if results:
        df = pd.DataFrame(results)
        # 중복 제목 제거
        df = df.drop_duplicates(subset=['제목']).reset_index(drop=True)
        
        # CSV 파일로 저장
        df.to_csv('latest_jobs.csv', index=False, encoding='utf-8-sig')
        
        # GitHub 저장소 메인에 표시될 README.md 문서 생성
        today = datetime.date.today().strftime('%Y년 %m월 %d일')
        md_text = f"# 🚗⚓ 오늘의 자동차·조선·재료 공고 알림 ({today})\n\n"
        md_text += f"총 **{len(df)}개**의 관심 공고를 찾았습니다.\n\n"
        md_text += "| 출처 | 제목 | 링크 | 등록일 |\n"
        md_text += "| :--- | :--- | :--- | :--- |\n"
        
        for _, row in df.iterrows():
            md_text += f"| {row['출처']} | {row['제목']} | [바로가기]({row['링크']}) | {row['등록일']} |\n"
            
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(md_text)
            
        print(f"\n✅ 수집 완료! 총 {len(df)}건의 공고가 저장되었습니다.")
    else:
        print("\n⚠️ 오늘 새로 조건에 맞는 공고가 없습니다.")
