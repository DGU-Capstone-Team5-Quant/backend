# Quant 문제 해결 가이드

## 🚨 자주 발생하는 문제

### 1. ModuleNotFoundError: No module named 'pydantic'

**증상:**
```
ModuleNotFoundError: No module named 'pydantic'
```

**원인:** 가상환경이 제대로 설정되지 않았습니다.

**해결:**
```bash
# 1. 가상환경 다시 생성
uv venv .venv

# 2. 의존성 설치
uv sync

# 3. CLI 재실행 (가상환경 활성화 불필요!)
python quant.py
```

**💡 참고:** `quant.py`는 자동으로 `.venv`를 찾아서 사용합니다!

---

### 2. Redis 연결 실패

**증상:**
```
✗ 연결 실패: Redis를 시작하세요
```

**해결:**

**로컬 Redis:**
```bash
# Docker 사용
docker run -d -p 6379:6379 redis:latest

# 또는 Windows용 Redis 설치
# https://github.com/microsoftarchive/redis/releases
```

**AWS Redis 사용:**
`.env` 파일에 AWS Redis 주소 설정:
```bash
REDIS_URL=redis://your-aws-redis-address:6379
```

---

### 3. Ollama 연결 실패

**증상:**
```
✗ 연결 안됨: Ollama를 시작하세요
```

**해결:**
```bash
# Ollama 설치 확인
ollama list

# Ollama 서버 시작
ollama serve

# 모델 다운로드
ollama pull llama3.1:8b
```

---

### 4. CLI가 Git Bash에서 멈춤

**증상:** Git Bash에서 실행 시 인터랙티브 메뉴가 작동하지 않음

**해결:**
```powershell
# PowerShell 또는 CMD에서 실행하세요
python quant.py
```

**이유:** `questionary` 라이브러리는 Windows 네이티브 터미널이 필요합니다.

---

### 5. 백테스트 결과가 없음

**증상:**
```
저장된 결과가 없습니다.
```

**해결:**
1. 백테스트를 한 번 이상 실행했는지 확인
2. `results/` 폴더가 존재하는지 확인
3. 파일 권한 문제가 있는지 확인

---

### 6. 메모리 초기화가 안됨

**증상:** 메모리 초기화 후에도 이전 데이터가 남아있음

**해결:**
```bash
# 수동으로 초기화
python scripts/reset_memory.py --all --yes

# Redis 완전 재시작
docker restart <redis-container-id>
```

---

### 7. 가상환경 활성화 문제

**PowerShell에서:**
```powershell
# 실행 정책 오류 시
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 활성화
.venv\Scripts\Activate.ps1
```

**Bash/Linux/Mac:**
```bash
source .venv/bin/activate
```

**하지만 Quant CLI는 가상환경 활성화가 필요 없습니다!**

---

## 🔍 디버깅 팁

### 시스템 상태 확인

```bash
# 대시보드에서 모든 상태 확인
python quant.py
→ 📈 대시보드
```

### 메모리 상태 확인

```bash
# CLI에서
python quant.py
→ 🧠 메모리 관리 → 📊 메모리 통계 조회

# 또는 스크립트로
python scripts/check_memory.py
```

### Python 환경 확인

```bash
# 현재 Python 경로
python -c "import sys; print(sys.executable)"

# pydantic 설치 확인
python -c "import pydantic; print(pydantic.__version__)"

# Redis 연결 테스트
python -c "import redis; r=redis.Redis(host='localhost', port=6379); print(r.ping())"
```

---

## 💡 모범 사례

### 실험 전 체크리스트

1. ✅ Ollama 실행 중인지 확인
2. ✅ Redis 실행 중인지 확인
3. ✅ 메모리 초기화 (`reset_memory.py --all`)
4. ✅ 시드 설정 (재현성)

### 백테스트 전 체크리스트

1. ✅ 티커 심볼 확인
2. ✅ 날짜 범위 확인 (과거 데이터만 가능)
3. ✅ 메모리 사용 여부 결정
4. ✅ 시드 설정

---

## 🆘 여전히 문제가 해결되지 않나요?

1. **로그 확인:**
   - `server.log` 파일 확인
   - 백테스트 출력 메시지 확인

2. **완전 초기화:**
   ```bash
   # 가상환경 삭제 및 재생성
   rm -rf .venv
   uv venv .venv
   uv sync

   # 메모리 초기화
   python scripts/reset_memory.py --all --yes

   # Redis 재시작
   docker restart <redis-container-id>
   ```

3. **GitHub Issues:**
   문제가 계속되면 이슈를 등록해주세요!
