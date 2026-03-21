// Live2D 모델 관리 클래스
class Live2DManager {
  constructor() {
    this.app = null;
    this.model = null;
    this.container = null;
    this.resizeObserver = null;
    this.resizeTimeout = null;
    
    // [신규] 초기화 상태 추적
    this.isInitialized = false;
    this.isInitializing = false;

    // 립싱크(Lip-sync) 관련 속성
    this.audioContext = null;
    this.analyser = null;
    this.dataArray = null;
    this.isLipSyncing = false;
    this.currentMouthValue = 0;
    this.isLoopRunning = false;
    
    // 입 모양 파라미터 ID 자동 탐색 결과
    this.mouthParamId = 'ParamMouthOpenY'; 
    
    // [신규] 커스텀 포즈 상태
    this.isListeningPose = false;

    // [추가] 오디오 인터셉터 원복을 위한 백업
    this.originalConnect = AudioNode.prototype.connect;
    
    // 모든 오디오 재생 시점을 감시하여 자동으로 립싱크 연결
    this._setupAudioInterceptor();
  }

  /**
   * [신규] 귀를 기울이는 자세 (커스텀 모션 재생)
   */
  startListeningPose() {
    if (!this.isInitialized) {
      console.warn('[Live2D] Cannot start listening pose: model not initialized yet');
      return;
    }
    
    this.isListeningPose = true;
    // 우선순위를 FORCE(2)로 주어 강제 재생
    if (this.model && this.model.motion) {
      this.model.motion('', 27, PIXI.live2d.MotionPriority.FORCE); 
    }
  }

  /**
   * [신규] 커스텀 자세 해제
   */
  stopListeningPose() {
    if (!this.isInitialized) {
      console.warn('[Live2D] Cannot stop listening pose: model not initialized yet');
      return;
    }
    
    this.isListeningPose = false;
    // 기본 자세(m2)로 복귀
    if (this.model && this.model.motion) {
      this.model.motion('', 0, PIXI.live2d.MotionPriority.FORCE);
    }
  }

  /**
   * [내부] AudioNode.prototype.connect를 가로채어,
   * 어떤 노드든 ctx.destination에 연결할 때 analyser를 사이에 삽입합니다.
   * 이 방식은 Howler.js, createBufferSource, MediaElementSource 등
   * 모든 Web Audio API 재생 방식에서 동작합니다.
   */
  _setupAudioInterceptor() {
    const self = this;
    // 인스턴스에 백업된 원본 함수 사용
    const originalConnect = this.originalConnect;

    AudioNode.prototype.connect = function(destination, ...args) {
      try {
        // destination이 AudioDestinationNode인 경우에만 가로채기
        if (destination instanceof AudioDestinationNode) {
          const ctx = this.context;

          // 녹음용 MediaStreamSource는 가로채지 않음 (마이크 → destination 직접 연결 방지)
          if (this.constructor.name === 'MediaStreamAudioSourceNode') {
            return originalConnect.call(this, destination, ...args);
          }

          // analyser가 없거나 다른 AudioContext의 것이면 새로 생성
          if (!self.analyser || self.audioContext !== ctx) {
            self.audioContext = ctx;
            self._createAnalyser(ctx);
            // analyser → destination 연결
            originalConnect.call(self.analyser, destination);
          }

          // source → analyser 연결
          const result = originalConnect.call(this, self.analyser, ...args);

          // 립싱크 자동 시작
          self.isLipSyncing = true;
          self._startAnimationLoop();

          return result;
        }
      } catch (e) {
        console.warn('[Live2D] Audio interceptor error, falling back:', e);
      }

      // destination이 아닌 경우 원래 동작 유지
      return originalConnect.call(this, destination, ...args);
    };
  }

  /**
   * [내부] AnalyserNode를 통일된 설정으로 생성합니다.
   */
  _createAnalyser(ctx) {
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 1024;
    this.analyser.smoothingTimeConstant = 0.0;
    this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
  }

  /**
   * [신규] 분석 루프를 안전하게 시작 (중복 실행 방지)
   */
  _startAnimationLoop() {
    if (this.isLoopRunning) return;
    this.isLoopRunning = true;
    this._updateLipSyncLoop();
  }

  /**
   * 요소가 DOM에 나타날 때까지 대기하는 헬퍼 함수
   */
  async _waitForElement(id, retryCount = 10) {
    for (let i = 0; i < retryCount; i++) {
      const el = document.getElementById(id);
      if (el) return el;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    return null;
  }

  /**
   * [신규] 외부(Flutter)에서 전달된 Base64 오디오 데이터를 재생합니다.
   * 재생 시 AnalyserNode 인터셉터가 자동으로 동작하여 립싱크가 발생합니다.
   */
  async playAudio(base64Data) {
    try {
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }

      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      // Base64를 ArrayBuffer로 변환
      const binaryString = atob(base64Data);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // 오디오 데이터 디코딩
      const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);
      
      // 소스 생성 및 연결
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      
      // [중요] 인터셉터가 AudioNode.prototype.connect를 가로채고 있으므로 
      // destination에 연결하면 자동으로 립싱크 분석기가 중간에 삽입됩니다.
      source.connect(this.audioContext.destination);
      
      source.start(0);
      console.log('[Live2D] PlayAudio started via WebView AudioContext');

      source.onended = () => {
        console.log('[Live2D] PlayAudio finished');
        // [모바일] Flutter로 재생 완료 신호 전송
        if (window.Live2DChannel) {
          window.Live2DChannel.postMessage('playbackFinished');
        }
      };
    } catch (e) {
      console.error('[Live2D] playAudio failed:', e);
    }
  }

  // Live2D 초기화
  async initialize(containerId, modelPath) {
    try {
      this.isInitializing = true;
      this.isInitialized = false;
      
      // [수정] 컨테이너가 나타날 때까지 최대 1초간 대기
      this.container = await this._waitForElement(containerId);
      
      if (!this.container) {
        throw new Error(`Container with id '${containerId}' not found after retries`);
      }
      
      // ResizeObserver 설정
      this.resizeObserver = new ResizeObserver(() => {
        clearTimeout(this.resizeTimeout);
        this.resizeTimeout = setTimeout(() => this.resize(), 100);
      });
      this.resizeObserver.observe(this.container);


      // PixiJS Application 생성
      try {
        // [신규] 로컬 파일 로드 이슈 완화를 위한 PIXI 설정
        if (window.PIXI) {
          PIXI.settings.CREATE_IMAGE_BITMAP = false;
        }

        this.app = new PIXI.Application({
          view: this.container,
          backgroundColor: 0xEFEBE0,
          backgroundAlpha: 1,
          width: this.container.offsetWidth || 800,
          height: this.container.offsetHeight || 600,
          autoStart: true,
          resolution: window.devicePixelRatio || 1,
          antialias: true,
          forceCanvas: true
        });
      } catch (error) {
        // Fallback for containerized environments
        this.app = new PIXI.Application({
          view: this.container,
          backgroundColor: 0xEFEBE0,
          backgroundAlpha: 1,
          width: this.container.offsetWidth || 800,
          height: this.container.offsetHeight || 600,
          autoStart: true,
          resolution: 1,
          antialias: true,
          rendererType: 1  // Canvas renderer
        });
      }

      // PIXI를 window에 노출 (자동 업데이트를 위해)
      window.PIXI = PIXI;

      // Live2D 모델 로드
      console.log('[Live2D] Loading model from:', modelPath);
      
      // CORS 이슈 해결을 위한 옵션 추가
      this.model = await PIXI.live2d.Live2DModel.from(modelPath, {
          autoInteract: true,
          crossOrigin: false // 로컬 파일이므로 CORS 사용 안함
      });

      // [신규] 모델 로드 즉시 기본 모션(m2, 인덱스 0)을 IDLE 우선순위로 재생
      // 이렇게 하면 m8(인사)과 같은 FORCE 모션이 끝난 뒤 자동으로 다시 m2로 돌아옵니다.
      if (this.model.internalModel && this.model.internalModel.motionManager) {
        this.model.motion('', 0, PIXI.live2d.MotionPriority.IDLE);
      }

      // 모델의 파라미터 조사
      this._findMouthParameter();

      // Stage에 모델 추가 및 인터랙션 설정
      this.app.stage.addChild(this.model);
      this.setupInteractions();

      // [신규] 모션 종료 이벤트 감시 로직
      // 어떤 모션(인사 등)이 끝나더라도 자동으로 뒷짐 자세(인덱스 0)로 돌아가게 함
      if (this.model.internalModel && this.model.internalModel.motionManager) {
        this.model.internalModel.motionManager.on('motionFinish', () => {
          // 커스텀 포즈 중이 아닐 때만 기본 자세로 복귀
          if (!this.isListeningPose) {
            this.model.motion('', 0, PIXI.live2d.MotionPriority.IDLE);
          }
        });
      }

    // Live2D 업데이트 사이클 내에서 립싱크 적용
    this.model.internalModel.on('beforeModelUpdate', () => {
      // 립싱크가 활성화되어 있고 값이 유효할 때만 적용
      if (this.isLipSyncing && this.currentMouthValue > 0) {
        this.model.internalModel.coreModel.setParameterValueById(
          this.mouthParamId, 
          this.currentMouthValue
        );
      }
    });

      this.model.on('modelUpdate', () => {
         // Animation updates handled
      });

      // 첫 렌더링 틱에서 리사이즈를 호출하여 정확한 초기 크기 설정
      this.app.ticker.addOnce(() => {
        this.resize();
      });

      // 초기화 완료 표시
      this.isInitializing = false;
      this.isInitialized = true;

      return true;
    } catch (error) {
      this.isInitializing = false;
      this.isInitialized = false;
      console.error('[Live2D] Initialization failed:', error);
      return false;
    }
  }

  /**
   * [내부] 모델의 파라미터를 조사하여 입 모양 제어용 ID를 찾습니다.
   */
  _findMouthParameter() {
    try {
      if (!this.model || !this.model.internalModel) return;
      
      const internalModel = this.model.internalModel;
      let parameterIds = [];
      
      if (internalModel.parameterIds) {
        parameterIds = internalModel.parameterIds;
      } else if (internalModel.coreModel && internalModel.coreModel._parameterIds) {
        parameterIds = internalModel.coreModel._parameterIds;
      }
      
      let foundId = 'ParamMouthOpenY'; 
      const candidates = ['ParamMouthOpenY', 'ParamA', 'MouthOpenY', 'MouthOpen', 'ParamMouthOpen'];
      
      for (const candidate of candidates) {
        if (parameterIds.includes(candidate)) {
          foundId = candidate;
          break;
        }
      }

      if (foundId === 'ParamMouthOpenY' && !parameterIds.includes('ParamMouthOpenY')) {
        for (const id of parameterIds) {
          const lowerId = id.toLowerCase();
          if (lowerId.includes('mouth') && lowerId.includes('open')) {
            foundId = id;
            break; 
          }
        }
      }

      this.mouthParamId = foundId;
    } catch (e) {
      this.mouthParamId = 'ParamMouthOpenY';
    }
  }

  // 인터랙션 설정
  setupInteractions() {
    if (!this.model) return;

    // 히트 테스트 이벤트
    this.model.on('hit', (hitAreas) => {
      
      // 예시: body를 클릭하면 특정 모션 재생
      if (hitAreas.includes('Body') || hitAreas.includes('body')) {
        this.playMotion('tap_body');
      }
      
      if (hitAreas.includes('Head') || hitAreas.includes('head')) {
        this.playMotion('tap_head');
      }
    });
  }

    // 모션 재생
    async playMotion(group, index = 0) {
      if (!this.isInitialized || !this.model) {
        console.warn(`[PlayMotion] Model not ready yet (initialized: ${this.isInitialized}, model: ${!!this.model}). Ignoring motion request for group="${group}", index=${index}`);
        return;
      }
      
      try {
        const internalModel = this.model.internalModel;
        if (internalModel && internalModel.motionManager) {
          const motionManager = internalModel.motionManager;
        }
        
        // 1. 요청된 모션 재생 (우선순위 FORCE)
        await this.model.motion(group, index, PIXI.live2d.MotionPriority.FORCE);
        
        // 2. 모션이 끝난 후, 재생했던 모션이 m2(0번)가 아니었다면 다시 m2로 복귀
        if (index !== 0 && !this.isListeningPose) {
          this.model.motion('', 0, PIXI.live2d.MotionPriority.IDLE);
        }
      } catch (error) {
        console.error(`[PlayMotion] Error for group="${group}", index=${index}:`, error);
      }
    }

  // 표정 변경
  setExpression(expressionName) {
    if (!this.isInitialized || !this.model) {
      console.warn(`[Live2D] Cannot set expression: model not ready yet (initialized: ${this.isInitialized}, model: ${!!this.model})`);
      return;
    }
    
    
    try {
      this.model.expression(expressionName);
    } catch (error) {
      console.error('Failed to set expression:', error);
    }
  }

  // 모델 위치 변경
  setPosition(x, y) {
    if (this.model) {
      this.model.x = x;
      this.model.y = y;
    }
  }

  // 모델 스케일 변경
  setScale(scale) {
    if (this.model) {
      this.model.scale.set(scale);
    }
  }

  /**
   * 입 열기 정도를 설정합니다. (수동 제어용)
   * @param {number} value 0.0 (닫힘) ~ 1.0 (최대로 열림)
   */
  setMouthOpen(value) {
    if (!this.isInitialized || !this.model) {
      return;
    }
    this.setParameterValue(this.mouthParamId, value);
  }

  /**
   * 특정 파라미터의 값을 직접 설정합니다.
   * @param {string} id 파라미터 ID (예: 'ParamAngleX', 'ParamMouthOpenY')
   * @param {number} value 설정할 값
   */
  setParameterValue(id, value) {
    if (this.model && this.model.internalModel && this.model.internalModel.coreModel) {
      this.model.internalModel.coreModel.setParameterValueById(id, value);
    }
  }

  /**
   * [신규] 현재 실시간 립싱크 진폭 값을 반환합니다. (0.0 ~ 1.0)
   */
  getLipSyncValue() {
    return this.currentMouthValue || 0;
  }

  startLipSync() {
    this.isLipSyncing = true;
    this._startAnimationLoop();
  }

  /**
   * [신규] 립싱크 중지
   */
  stopLipSync() {
    this.isLipSyncing = false;
    this.currentMouthValue = 0;
    
    // [추가] 립싱크 중지 시 입 모양을 강제로 닫아 모션 제어 간섭 방지
    if (this.model && this.model.internalModel && this.model.internalModel.coreModel) {
      this.model.internalModel.coreModel.setParameterValueById(this.mouthParamId, 0);
    }
  }

  /**
    * [내부] 실시간 진폭 분석 루프
    */
  _updateLipSyncLoop() {
    if (!this.isLipSyncing || !this.analyser || !this.model) {
      this.isLoopRunning = false;
      return;
    }

    this.analyser.getByteTimeDomainData(this.dataArray);
    
     // RMS (Root Mean Square) — 에너지 기반으로 목소리 진폭을 정확하게 추출
    let sumSquares = 0;
    for (let i = 0; i < this.dataArray.length; i++) {
      const normalized = (this.dataArray[i] - 128) / 128.0;
       sumSquares += normalized * normalized;
    }
    const rms = Math.sqrt(sumSquares / this.dataArray.length);

     let targetMouth = Math.min(rms * 7.0, 1.0);
    if (targetMouth < 0.015) targetMouth = 0;

     // Lerp: 열기는 빠르게(0.5), 닫기는 느리게(0.2) — 자연스러운 입 관성
    const lerpSpeed = targetMouth > this.currentMouthValue ? 0.85 : 0.5;
     this.currentMouthValue += (targetMouth - this.currentMouthValue) * lerpSpeed;

    if (this.audioContext && this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }

    requestAnimationFrame(() => this._updateLipSyncLoop());
  }

  // 리사이즈 처리
  resize() {
    if (!this.app || !this.model) {
      return;
    }
    
    // 컨테이너 크기 가져오기
    const containerWidth = this.container.clientWidth;
    const containerHeight = this.container.clientHeight;
    
    // renderer 크기를 명시적으로 업데이트
    this.app.renderer.resize(containerWidth, containerHeight);
    
    const screen = this.app.screen;
    
    // 모델의 위치와 앵커 설정
    this.model.anchor.set(0.5, 0.5);
    this.model.x = screen.width / 2;
    // [수정] 모델이 커졌으므로 y축 위치를 화면 중앙(0.5)보다 아래(1.1)로 내려서 머리가 안 잘리게 함
    this.model.y = screen.height * 1.1;

    // 모델의 스케일 재계산
    const modelWidth = this.model.internalModel.width;
    const modelHeight = this.model.internalModel.height;

    // [수정] 스케일 계수를 0.8에서 2.0로 키워 캐릭터를 크게 표시
    const scale = Math.min(
      screen.width / modelWidth,
      screen.height / modelHeight
    ) * 2.0;
    this.model.scale.set(scale);
  }

  // 정리
  destroy() {
    this.stopLipSync();

    // [추가] 오디오 인터셉터 원복
    if (this.originalConnect) {
      AudioNode.prototype.connect = this.originalConnect;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    
    if (this.app) {
      this.app.destroy(true); // view(canvas)도 함께 제거
      this.app = null;
    }
    this.model = null; 
  }
}

// 전역 인스턴스 초기화 시도 함수
function initLive2DManager() {
  if (window.PIXI && window.PIXI.live2d && window.PIXI.live2d.Live2DModel) {
    console.log('[Live2D-Init] SDK found, creating manager instance');
    window.live2dManager = new Live2DManager();
    return true;
  }
  return false;
}

// 초기화 시도 루프
(function attemptInit() {
  if (!initLive2DManager()) {
    console.log('[Live2D-Init] Waiting for SDK libs...');
    setTimeout(attemptInit, 200);
  }
})();
