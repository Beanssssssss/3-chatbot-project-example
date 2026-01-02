# 🎨 Render 배포 가이드

이 가이드는 Render 플랫폼에 챗봇 애플리케이션을 배포하는 단계별 가이드입니다.

---

## 📋 사전 준비사항

1. **GitHub 저장소 준비**
   - 프로젝트가 GitHub에 푸시되어 있어야 합니다
   - 모든 파일이 커밋되어 있어야 합니다

2. **OpenAI API 키 준비**
   - OpenAI API 키가 필요합니다
   - https://platform.openai.com/api-keys 에서 발급 가능

---

## 🚀 배포 단계

### 1단계: Render 계정 생성

1. https://render.com 접속
2. "Get Started for Free" 클릭
3. GitHub 계정으로 로그인
4. GitHub 저장소 접근 권한 허용

### 2단계: Web Service 생성

1. **Dashboard에서 "New +" 버튼 클릭**
2. **"Web Service" 선택**
3. **저장소 연결**
   - "Connect account" 또는 "Connect repository" 클릭
   - 배포할 GitHub 저장소 선택
   - "Connect" 클릭

### 3단계: 서비스 설정

다음 정보를 입력합니다:

#### 기본 설정
- **Name**: `chatbot-app` (원하는 이름으로 변경 가능)
- **Region**: `Seoul` 또는 가장 가까운 지역 선택
- **Branch**: `main` (또는 기본 브랜치)
- **Root Directory**: `.` (루트 디렉토리)

#### 빌드 및 시작 명령어
- **Environment**: `Python 3`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt && python3 makedb.py
  ```
- **Start Command**: 
  ```bash
  gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  ```

#### 인스턴스 설정
- **Instance Type**: 
  - 무료 플랜: `Free` (제한적)
  - 권장: `Starter` ($7/월) - 더 안정적
- **Auto-Deploy**: `Yes` (GitHub 푸시 시 자동 배포)

### 4단계: 환경 변수 설정

1. **"Environment" 섹션으로 스크롤**
2. **"Add Environment Variable" 클릭**
3. **다음 변수 추가**:
   - **Key**: `OPENAI_API_KEY`
   - **Value**: 실제 OpenAI API 키 입력
   - **"Save Changes" 클릭**

### 5단계: Persistent Disk 추가 (선택사항)

> ⚠️ **무료 플랜 사용자**: 이 단계는 **건너뛰세요**. 무료 플랜에서는 Persistent Disk를 사용할 수 없습니다.
> 
> 무료 플랜에서는:
> - 빌드 시 DB가 생성되어 런타임에 사용됩니다
> - 새로운 데이터 저장은 실패하지만, 기존 DB 읽기는 정상 작동합니다
> - 서비스 재시작 시 DB가 초기화될 수 있습니다

**Starter 플랜 이상 사용자만** Persistent Disk를 추가하세요:

1. **"Disk" 섹션으로 스크롤**
2. **"Add Disk" 클릭**
3. **다음 설정 입력**:
   - **Name**: `chatbot-disk`
   - **Mount Path**: `/opt/render/project/src`
   - **Size**: `10 GB` (필요에 따라 조정)
4. **"Add Disk" 클릭**

### 6단계: 배포 시작

1. **모든 설정 확인**
2. **"Create Web Service" 버튼 클릭**
3. **배포 진행 상황 확인**
   - 로그를 통해 빌드 및 배포 과정 확인
   - 일반적으로 5-10분 소요

---

## 🔍 배포 확인

### 배포 성공 확인

1. **배포 완료 후 제공되는 URL 확인**
   - 예: `https://chatbot-app.onrender.com`
2. **브라우저에서 URL 접속**
3. **챗봇 선택 페이지가 정상적으로 표시되는지 확인**

### 로그 확인

1. **Dashboard → 서비스 선택**
2. **"Logs" 탭 클릭**
3. **에러가 있는지 확인**

---

## ⚙️ render.yaml 파일 사용 (선택사항)

`render.yaml` 파일을 사용하면 코드로 인프라를 관리할 수 있습니다.

### 장점
- 설정을 코드로 관리
- 버전 관리 가능
- 여러 환경 관리 용이

### 사용 방법

1. **저장소에 `render.yaml` 파일이 있는지 확인**
2. **Render Dashboard에서 "New +" → "Blueprint" 선택**
3. **저장소 연결**
4. **자동으로 `render.yaml` 설정 적용**

---

## 🔧 문제 해결

### 문제 1: 빌드 실패

**증상**: Build Command 실행 중 오류

**해결 방법**:
1. 로그에서 정확한 오류 메시지 확인
2. `requirements.txt`의 패키지 버전 확인
3. Python 버전 확인 (runtime.txt 확인)

### 문제 2: 502 Bad Gateway

**증상**: 배포 후 접속 시 502 에러

**해결 방법**:
1. 로그에서 Gunicorn 실행 여부 확인
2. 포트 번호 확인 (`$PORT` 환경 변수)
3. Start Command 확인
4. 인스턴스 타입이 너무 작은지 확인 (최소 Starter 권장)

### 문제 3: ChromaDB 파일을 찾을 수 없음

**증상**: 데이터베이스 관련 오류

**해결 방법**:
1. **무료 플랜 사용자**: 
   - 빌드 로그에서 `makedb.py` 실행 여부 확인
   - DB는 빌드 시 생성되므로 런타임에는 읽기만 가능
   - 새로운 데이터 저장 실패는 정상 (에러 무시됨)
2. **Starter 플랜 이상 사용자**:
   - Persistent Disk가 제대로 마운트되었는지 확인
   - 마운트 경로 확인 (`/opt/render/project/src`)
   - `makedb.py`가 빌드 시 실행되었는지 확인

### 문제 4: 메모리 부족

**증상**: 애플리케이션이 자주 재시작됨

**해결 방법**:
1. Worker 수 줄이기 (Start Command에서 `--workers 1`)
2. 더 큰 인스턴스 타입 사용
3. 타임아웃 시간 조정

### 문제 5: 무료 플랜 제한

**증상**: 
- 15분 비활성 후 자동 스핀다운
- Persistent Disk 사용 불가
- DB 저장 실패 (읽기는 가능)

**해결 방법**:
- **무료 플랜 사용 시**: 
  - DB는 빌드 시 생성되어 읽기 전용으로 사용
  - 새로운 데이터 저장 실패는 정상 (에러 무시됨)
  - 서비스 재시작 시 DB가 초기화될 수 있음
- **영구 저장이 필요한 경우**:
  - Starter 플랜 ($7/월) 이상 사용 권장
  - 또는 다른 플랫폼 (Railway 등) 고려

---

## 💰 비용 안내

### 무료 플랜
- ✅ 무료
- ❌ 15분 비활성 후 스핀다운
- ❌ Persistent Disk 사용 불가
- ⚠️ DB는 빌드 시 생성, 런타임에는 읽기만 가능
- ⚠️ 새로운 데이터 저장 실패 (에러 무시됨)
- ✅ 기본 기능은 정상 작동 (RAG 검색, 응답 생성 등)

### Starter 플랜 ($7/월)
- ✅ Persistent Disk 사용 가능
- ✅ 자동 스핀다운 없음
- ✅ 512MB RAM
- ✅ DB 영구 저장 가능
- ✅ 새로운 데이터 저장 가능
- ✅ 권장 플랜 (프로덕션 환경)

### Standard 플랜 ($25/월)
- ✅ 더 많은 리소스
- ✅ 더 빠른 성능
- ✅ 프로덕션 환경에 적합

---

## 🔄 업데이트 및 재배포

### 자동 배포
- GitHub에 푸시하면 자동으로 재배포됩니다
- `Auto-Deploy` 설정이 활성화되어 있어야 합니다

### 수동 재배포
1. Dashboard → 서비스 선택
2. "Manual Deploy" → "Deploy latest commit" 클릭

### 환경 변수 업데이트
1. Dashboard → 서비스 선택
2. "Environment" 탭
3. 변수 수정 후 "Save Changes"
4. 자동으로 재시작됨

---

## 📊 모니터링

### 로그 확인
- 실시간 로그: Dashboard → 서비스 → "Logs" 탭
- 로그 다운로드: "Download Logs" 버튼

### 메트릭 확인
- CPU, 메모리 사용량: Dashboard → 서비스 → "Metrics" 탭
- 요청 수, 응답 시간 등 확인 가능

---

## 🔐 보안 권장사항

1. **환경 변수 보안**
   - API 키는 절대 코드에 하드코딩하지 마세요
   - Render의 환경 변수 기능 사용

2. **HTTPS**
   - Render는 자동으로 HTTPS 제공
   - 커스텀 도메인도 HTTPS 지원

3. **접근 제한** (필요시)
   - Render의 Private Service 기능 사용
   - 특정 IP만 접근 허용

---

## 📚 추가 리소스

- [Render 공식 문서](https://render.com/docs)
- [Python 배포 가이드](https://render.com/docs/deploy-python)
- [Persistent Disk 가이드](https://render.com/docs/disks)

---

## ✅ 체크리스트

배포 전 확인사항:

- [ ] GitHub 저장소에 모든 파일 푸시됨
- [ ] `requirements.txt`에 모든 의존성 포함
- [ ] `render.yaml` 파일 확인 (선택사항)
- [ ] `runtime.txt` 파일 확인 (Python 버전)
- [ ] OpenAI API 키 준비됨
- [ ] Render 계정 생성됨
- [ ] 플랜 선택 (무료 플랜 또는 Starter 플랜 이상)

배포 후 확인사항:

- [ ] 애플리케이션이 정상적으로 실행됨
- [ ] 로그에 에러가 없음
- [ ] 챗봇이 정상적으로 응답함
- [ ] ChromaDB 파일이 제대로 저장됨
- [ ] 환경 변수가 올바르게 설정됨

---

**행운을 빕니다! 🚀**
