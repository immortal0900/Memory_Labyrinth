# Supabase 배포 및 설정 가이드

이 가이드는 로컬에서 개발한 PostgreSQL + pgvector 환경을 Supabase 클라우드에 배포하는 방법을 설명합니다.

## 1. Supabase 프로젝트 생성

1. [Supabase](https://supabase.com/)에 로그인하고 'New Project'를 클릭합니다.
2. Organization을 선택하고 프로젝트 이름(예: `game-db`)과 비밀번호를 설정합니다.
   > **중요:** 데이터베이스 비밀번호는 꼭 기억해두거나 안전한 곳에 저장하세요!
3. Region은 한국(Seoul) 또는 가장 가까운 곳을 선택합니다.
4. 'Create new project'를 클릭하고 생성이 완료될 때까지 기다립니다.

## 2. pgvector 확장 기능 활성화

1. 왼쪽 메뉴에서 **Database** 아이콘을 클릭합니다.
2. **Extensions** 메뉴를 선택합니다.
3. 검색창에 `vector`를 입력합니다.
4. `vector` (pgvector) 확장의 상태 스위치를 켜서 활성화합니다.
   > **참고:** `init.sql` 스크립트의 첫 줄에도 활성화 명령어가 포함되어 있지만, 확실하게 하기 위해 UI에서 확인하는 것이 좋습니다.

## 3. 테이블 생성 (SQL 실행)

1. 왼쪽 메뉴에서 **SQL Editor** 아이콘을 클릭합니다.
2. 'New Query'를 클릭합니다.
3. 프로젝트 폴더에 있는 `init.sql` 파일의 내용을 모두 복사하여 붙여넣습니다.
4. 우측 하단의 **Run** 버튼을 클릭하여 실행합니다.
5. 'Success' 메시지가 뜨면 테이블 생성이 완료된 것입니다.
6. **Table Editor** 메뉴로 가서 테이블들이(`monsters`, `items` 등) 잘 생성되었는지 확인합니다.

## 4. 환경 변수 설정 (.env)

로컬 프로젝트의 `.env` 파일을 수정하여 Supabase와 연결합니다.

1. Supabase 대시보드에서 **Project Settings** (톱니바퀴 아이콘) -> **Database**로 이동합니다.
2. **Connection string** 섹션에서 **URI** 탭을 선택합니다.
3. 주소를 복사합니다.
   - 형식: `postgresql://postgres.xxxx:password@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres`
   - **주의:** `Mode: Transaction` (포트 6543)을 권장합니다. Session 모드(5432)도 가능합니다.
4. `.env` 파일의 `DATABASE_URL` 값을 수정합니다.
   - `[YOUR-PASSWORD]` 부분을 아까 설정한 실제 비밀번호로 변경해야 합니다.
   - `postgresql://`을 `postgresql+psycopg://`로 변경하면 Python 라이브러리와 더 잘 호환됩니다.

**예시:**
```env
DATABASE_URL=postgresql+psycopg://postgres.abcdefg:mypassword123@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
```

## 5. 로컬 테스트

1. `uv sync` 명령어로 의존성 패키지를 업데이트합니다.
2. 코드를 실행하여 DB 연결 및 데이터 저장이 잘 되는지 확인합니다.

## 6. 문제 해결

- **연결 오류:** 비밀번호가 맞는지, URL 형식이 올바른지 확인하세요. 특수문자가 비밀번호에 있다면 URL 인코딩이 필요할 수 있습니다.
- **벡터 오류:** `vector` 확장이 켜져 있는지 다시 확인하세요.

