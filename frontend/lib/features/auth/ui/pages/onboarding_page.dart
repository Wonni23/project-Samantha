import 'package:flutter/material.dart';
import 'dart:async'; // Add this import for unawaited
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:frontend/features/auth/data/models/profile_setup.dart';
import 'package:frontend/core/router/router_paths.dart';
import 'package:frontend/features/auth/data/repositories/auth_repository.dart';

class OnboardingProfilePage extends ConsumerStatefulWidget {
  const OnboardingProfilePage({super.key});

  @override
  ConsumerState<OnboardingProfilePage> createState() =>
      _OnboardingProfilePageState();
}

class _OnboardingProfilePageState extends ConsumerState<OnboardingProfilePage> {
  final _formKey = GlobalKey<FormState>();

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _birthYearController = TextEditingController();
  final TextEditingController _titleController = TextEditingController();

  // ★ 변경점 1: 기본값을 빼고 'GenderType?' (물음표)를 붙여서 비어있는 상태로 시작합니다.
  GenderType? _selectedGender;
  bool _isLoading = false;

  @override
  void dispose() {
    _nameController.dispose();
    _birthYearController.dispose();
    _titleController.dispose();
    super.dispose();
  }

  Future<void> _submitProfile() async {
    if (_isLoading) return; // 중복 제출 방지

    // 1. 폼 유효성 검사
    if (!_formKey.currentState!.validate()) {
      return;
    }

    // 2. 성별 선택 검사
    if (_selectedGender == null) {
      // 선택 안 했으면 스낵바(하단 알림창)를 띄웁니다.
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('성별을 선택해주세요!'),
          backgroundColor: Colors.red,
        ),
      );
      return; // 함수 강제 종료 (다음 페이지로 못 감)
    }

    // 3. 로딩 시작 및 API 호출
    setState(() {
      _isLoading = true;
    });

    try {
      final profileData = ProfileSetupRequest(
        realName: _nameController.text,
        gender: _selectedGender!, // ★ 느낌표(!)는 "위에서 검사했으니 절대 null 아님"이라는 뜻
        birthYear: int.parse(_birthYearController.text),
        userTitle: _titleController.text.isEmpty
            ? '선생님'
            : _titleController.text,
        platform: PlatformType.web, // 예시로 web 사용, 실제 앱에서는 동적으로 결정
      );

      // AuthRepository를 통해 API 호출
      await ref.read(authRepositoryProvider).setupProfile(profileData);

      // 4. 성공 시 다음 페이지로 이동
      // BuildContext를 async gap 전에 캡처하여 lint 경고를 회피하고 안정성을 높입니다.
      final currentContext = context;
      if (currentContext.mounted) {
        unawaited(currentContext.push(AppRoutePaths.onboardingTerms));
      }
    } catch (e) {
      // 5. 실패 시 에러 메시지 표시
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('프로필 저장 중 오류가 발생했습니다. 다시 시도해 주세요.'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      // 6. 로딩 종료
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('프로필 설정 (1/2)')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: ListView(
            children: [
              const SizedBox(height: 20),

              // 1. 실명 입력
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: '실명 (필수)',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.person),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '이름을 입력해주세요!';
                  }
                  if (value.length < 2) {
                    return '이름은 2글자 이상이어야 합니다.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 20),

              // 2. 호칭 입력
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'AI가 부를 호칭 (선택)',
                  hintText: '예: 오빠, 누님, 선생님 (기본값: 선생님)',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.record_voice_over),
                ),
              ),
              const SizedBox(height: 20),

              // 3. 출생년도 입력
              TextFormField(
                controller: _birthYearController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: '출생년도 (필수)',
                  hintText: '예: 1960',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.calendar_today),
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return '출생년도를 입력해주세요.';
                  }
                  final year = int.tryParse(value);
                  if (year == null || year < 1900 || year > 2026) {
                    return '올바른 년도를 입력해주세요 (1900~2026)';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 20),

              // 4. 성별 선택 (필수 표시 추가)
              const Row(
                children: [
                  Text(
                    '성별',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(width: 5),
                  Text(
                    '*',
                    style: TextStyle(color: Colors.red, fontSize: 16),
                  ), // 빨간 별표
                ],
              ),
              const SizedBox(height: 8),

              // ★ 변경점 3: 성별 선택 UI
              Container(
                decoration: BoxDecoration(
                  // 선택 안 했을 때 시각적으로 알려주기 위해 테두리를 칠할 수도 있습니다 (지금은 기본)
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(5),
                ),
                child: RadioGroup<GenderType>(
                  onChanged: (value) {
                    setState(() {
                      _selectedGender = value;
                    });
                  },
                  groupValue: _selectedGender,
                  child: const Column(
                    children: [
                      RadioListTile<GenderType>(
                        title: Text('남성'),
                        value: GenderType.male,
                      ),
                      Divider(height: 1),
                      RadioListTile<GenderType>(
                        title: Text('여성'),
                        value: GenderType.female,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 40),
              // 제출 버튼
              ElevatedButton(
                onPressed: _submitProfile,
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size(double.infinity, 50),
                ),
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text('다음 단계로', style: TextStyle(fontSize: 18)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
