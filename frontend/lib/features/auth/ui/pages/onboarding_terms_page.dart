import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/auth/data/models/terms_agree.dart';
import 'package:frontend/features/auth/data/repositories/auth_repository.dart';
import 'package:frontend/features/auth/providers/auth_provider.dart';

class OnboardingTermsPage extends ConsumerStatefulWidget {
  const OnboardingTermsPage({super.key});

  @override
  ConsumerState<OnboardingTermsPage> createState() =>
      _OnboardingTermsPageState();
}

class _OnboardingTermsPageState extends ConsumerState<OnboardingTermsPage> {
  // 체크박스 상태 변수들
  bool _termsOfService = false;
  bool _privacyPolicy = false;
  bool _voiceCollection = false;
  bool _marketingConsent = false;
  bool _isLoading = false;

  // 전체 동의 상태 확인
  bool get _isAllChecked =>
      _termsOfService && _privacyPolicy && _voiceCollection && _marketingConsent;

  // 필수 항목 동의 상태 확인
  bool get _isAllRequiredChecked =>
      _termsOfService && _privacyPolicy && _voiceCollection;

  // 전체 동의 토글 로직
  void _toggleAll(bool? value) {
    final newValue = value ?? false;
    setState(() {
      _termsOfService = newValue;
      _privacyPolicy = newValue;
      _voiceCollection = newValue;
      _marketingConsent = newValue;
    });
  }

  Future<void> _submitOnboarding() async {
    if (_isLoading) return; // 중복 요청 방지

    final termsData = TermsAgreeRequest(
      termsOfService: _termsOfService,
      privacyPolicy: _privacyPolicy,
      voiceCollection: _voiceCollection,
      marketingConsent: _marketingConsent,
    );

    setState(() {
      _isLoading = true;
    });

    try {
      // 1. 약관 동의 정보 백엔드 전송
      await ref.read(authRepositoryProvider).agreeToTerms(termsData);

      // 2. 프런트엔드 인증 상태를 '로그인 완료'로 변경 (자동 리디렉션 트리거)
      await ref.read(authProvider.notifier).completeOnboarding();
      
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('약관 동의 중 오류가 발생했습니다. 다시 시도해 주세요.'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  // 중복되는 코드를 줄이기 위해 만든 '약관 아이템' 위젯 함수
  Widget _buildTermItem({
    required String title,
    required String content,
    required bool value,
    required ValueChanged<bool?> onChanged,
    bool isRequired = true,
  }) {
    final theme = Theme.of(context);
    
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      margin: const EdgeInsets.only(bottom: 12),
      child: Theme(
        // ExpansionTile 기본 구분선 제거
        data: theme.copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
          leading: Checkbox(
            value: value,
            onChanged: onChanged,
            activeColor: Colors.deepPurple,
          ),
          title: Row(
            children: [
              Text(
                isRequired ? '[필수] ' : '[선택] ',
                style: TextStyle(
                  color: isRequired ? Colors.deepPurple : Colors.grey.shade600,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                content,
                style: TextStyle(
                  fontSize: 13,
                  color: Colors.grey.shade700,
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('약관 동의 (2/2)')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              // 스크롤 가능한 약관 리스트 영역
              Expanded(
                child: ListView(
                  children: [
                    const Text(
                      '서비스 이용을 위해\n약관에 동의해주세요.',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 24),

                    // ★ 추가된 기능: 전체 동의 체크박스
                    Container(
                      decoration: BoxDecoration(
                        color: Colors.deepPurple.withValues(alpha: 0.08), // 변경됨
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.deepPurple.withValues(alpha: 0.3)), // 변경됨
                      ),
                      child: CheckboxListTile(
                        value: _isAllChecked,
                        onChanged: _toggleAll,
                        activeColor: Colors.deepPurple,
                        title: const Text(
                          '약관 전체 동의하기',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        controlAffinity: ListTileControlAffinity.leading,
                      ),
                    ),
                    const SizedBox(height: 16),

                    // 1. 서비스 이용약관 (기존 텍스트 전체 복구)
                    _buildTermItem(
                      title: '서비스 이용약관',
                      value: _termsOfService,
                      onChanged: (v) => setState(() => _termsOfService = v!),
                      content: """
제1조 (목적)
본 약관은 Samantha 서비스(이하 '서비스')의 이용과 관련하여 회사와 회원 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.

제2조 (용어의 정의)
1. '서비스'란 구현되는 단말기와 상관없이 회원이 이용할 수 있는 Samantha 제반 서비스를 의미합니다.
2. '회원'이란 회사의 서비스에 접속하여 본 약관에 따라 회사와 이용계약을 체결하고 회사가 제공하는 서비스를 이용하는 고객을 말합니다.

제3조 (약관의 효력)
본 약관은 서비스를 신청한 고객이 동의함으로써 효력이 발생합니다.""",
                    ),

                    // 2. 개인정보 처리방침 (기존 텍스트 전체 복구)
                    _buildTermItem(
                      title: '개인정보 처리방침',
                      value: _privacyPolicy,
                      onChanged: (v) => setState(() => _privacyPolicy = v!),
                      content: '''
1. 수집하는 개인정보 항목
회사는 회원가입, 원활한 고객상담, 서비스 제공을 위해 아래와 같은 개인정보를 수집하고 있습니다.
- 필수항목: 이름, 출생년도, 성별
- 선택항목: 호칭

2. 개인정보의 수집 및 이용목적
- 서비스 가입 의사 확인, 연령 확인
- 맞춤형 AI 서비스 제공 (호칭 사용 등)
- 법령 및 약관 위반시 제재 조치''',
                    ),

                    // 3. 음성 수집 동의 (기존 텍스트 전체 복구)
                    _buildTermItem(
                      title: '음성 수집 및 이용 동의',
                      value: _voiceCollection,
                      onChanged: (v) => setState(() => _voiceCollection = v!),
                      content: '''
본 서비스는 AI와의 대화를 위해 사용자의 음성 데이터를 수집 및 이용합니다.

1. 수집 목적: AI 대화 기능 제공 및 음성 인식 정확도 향상
2. 수집 항목: 사용자의 발화 음성 데이터
3. 보유 기간: 서비스 탈퇴 시까지 (단, 법령에 따른 보존 필요 시 해당 기간까지)

* 귀하는 음성 데이터 수집 거부 권리가 있으나, 거부 시 AI 음성 대화 서비스 이용이 제한될 수 있습니다.''',
                    ),

                    // 4. 마케팅 동의 (기존 텍스트 전체 복구)
                    _buildTermItem(
                      title: '마케팅 정보 수신 동의',
                      value: _marketingConsent,
                      isRequired: false, // 선택 항목
                      onChanged: (v) => setState(() => _marketingConsent = v!),
                      content: '''
새로운 기능 업데이트, 이벤트 정보, 맞춤형 혜택 등 다양한 정보를 받으실 수 있습니다.
동의하지 않으셔도 기본 서비스 이용에는 제한이 없습니다.''',
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 10),

              // 하단 고정 버튼 (디자인 및 터치 영역 개선 반영)
              SizedBox(
                width: double.infinity,
                height: 52, // 높이를 50에서 52로 약간 키워 터치성 향상
                child: ElevatedButton(
                  onPressed: _isAllRequiredChecked ? _submitOnboarding : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepPurple, // 활성화 색상
                    foregroundColor: Colors.white, // 글자 색상
                    disabledBackgroundColor: Colors.grey.shade300, // 비활성화 배경
                    disabledForegroundColor: Colors.grey.shade500, // 비활성화 글자
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                        )
                      : const Text('가입 완료', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}