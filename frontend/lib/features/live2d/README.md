# Live2D Integration for Flutter Web

이 프로젝트는 Flutter Web에서 Live2D 모델을 표시하기 위한 통합 구현입니다.

## 아키텍처

```
Flutter Web App
    ↓
HtmlElementView (Flutter Widget)
    ↓
HTML Canvas Element
    ↓
PixiJS + pixi-live2d-display
    ↓
Live2D Cubism Core
```

## 사용된 라이브러리

- **[pixi-live2d-display](https://github.com/guansss/pixi-live2d-display)** - Live2D를 PixiJS에서 쉽게 사용할 수 있게 해주는 라이브러리
- **[PixiJS](https://pixijs.com/)** - 2D WebGL 렌더링 라이브러리
- **Live2D Cubism Core** - Live2D의 핵심 렌더링 엔진

## 설정 방법

### 1. Live2D 모델 준비

Live2D 모델 파일들을 `web/live2d_model/` 디렉토리에 배치합니다:

```
web/
  live2d_model/
    model.model3.json  (또는 .model.json for Cubism 2.1)
    *.moc3             (모델 데이터)
    textures/          (텍스처 이미지들)
    motions/           (모션 파일들)
    expressions/       (표정 파일들)
```

### 2. Flutter에서 사용

```dart
import 'package:frontend/features/live2d/live2d_widget.dart';

// 기본 사용
Live2DWidget(
  modelPath: 'live2d_model/model.model3.json',
  width: 600,
  height: 600,
)
```

### 3. 모션 및 표정 제어

```dart
final GlobalKey<_Live2DWidgetState> live2dKey = GlobalKey();

// 위젯 생성
Live2DWidget(
  key: live2dKey,
  modelPath: 'live2d_model/model.model3.json',
)

// 모션 재생
live2dKey.currentState?.playMotion('idle');
live2dKey.currentState?.playMotion('tap_body', 0);

// 표정 변경
live2dKey.currentState?.setExpression('happy');
```

## 지원 기능

- ✅ Cubism 2.1, 3, 4 모델 모두 지원
- ✅ 자동 마우스 트래킹 (시선 따라가기)
- ✅ 히트 영역 클릭 감지
- ✅ 모션 재생
- ✅ 표정 변경
- ✅ 투명 배경 지원
- ✅ 반응형 크기 조절

## JavaScript API

직접 JavaScript를 호출하여 제어할 수도 있습니다:

```javascript
// 모델 초기화
await window.live2dManager.initialize('canvas-id', 'live2d_model/model.model3.json');

// 모션 재생
window.live2dManager.playMotion('tap_body', 0);

// 표정 변경
window.live2dManager.setExpression('happy');

// 위치 변경
window.live2dManager.setPosition(100, 200);

// 스케일 변경
window.live2dManager.setScale(1.5);

// 정리
window.live2dManager.destroy();
```

## 참고 자료

- [pixi-live2d-display GitHub](https://github.com/guansss/pixi-live2d-display)
- [pixi-live2d-display 문서](https://guansss.github.io/pixi-live2d-display)
- [Live2D 공식 사이트](https://www.live2d.com/)
- [PixiJS 문서](https://pixijs.download/release/docs/index.html)

## 예시 프로젝트

- [Live2D Viewer Online](https://guansss.github.io/live2d-viewer-web/) - pixi-live2d-display를 사용한 온라인 뷰어
- [Basic Demo](https://codepen.io/guansss/pen/oNzoNoz/left?editors=1010)
- [Interaction Demo](https://codepen.io/guansss/pen/KKgXBOP/left?editors=0010)

## 문제 해결

### 모델이 로드되지 않는 경우

1. 브라우저 콘솔에서 에러 확인
2. 모델 경로가 올바른지 확인 (`web/` 디렉토리 기준)
3. 모델 파일 구조가 올바른지 확인

### 성능 문제

- 모델 스케일을 적절히 조정하세요
- 여러 모델을 동시에 표시할 경우 리소스 사용량에 주의하세요

### CORS 문제

로컬 개발 시 `flutter run -d chrome --web-browser-flag "--disable-web-security"` 사용 (개발 환경에서만!)

## 라이선스

이 통합 코드는 MIT 라이선스를 따릅니다.
Live2D 모델 사용 시 Live2D의 라이선스 정책을 확인하세요.
