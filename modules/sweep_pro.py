'''
sweep = 기출 문제집

1. 목차
- squeeze와 비슷하게...
- 6개 단원 큰 목차 아래에 topic 넣기

2. 문제
- 6개 단원 쪼개서 제작되어야 함
- 문항 번호 : 글꼴을 고딕스럽게
- 문항 출처 : 우측 정렬, |2026학년도 대수능 14번 지1| / |2021년 4월 13번 지1|
- 문항 내용 : Overlay
-- 2개 이상의 문항이 한 단으로 배치가 가능함
-- minimal interval == 30 정도로 설정
-- semi-justify and variable split
- 문항 modifiation : Overlay **뒤의 단원들도 보고 정해야함
- 단원 구분 띠지: 우수 page의 우측에 띠지로 표기

3. 빠른 정답
- 단원 합쳐서 제작해야 함
- 1개 page가 아니라 여러 page가 가능함에 유의

4. 해설
- 6개 단원 쪼개서 제작하기
- 해설 문두 바꾸기
- 해설 내용 : Overlay

5. 추가 사항
- 구현 방식
-- 목차 / 문제1 문제2 .. 문제6 / 빠른 정답 / 해설1 해설2 .. 해설6 을 각각 pdf로 만들기
-- 각 pdf를 합쳐서 최종 pdf 만들기
'''