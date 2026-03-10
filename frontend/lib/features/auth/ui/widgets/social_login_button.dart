import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class SocialLoginButton extends StatelessWidget {
  final String text;
  final String logoAsset;
  final Color backgroundColor;
  final Color textColor;
  final VoidCallback? onPressed;

  const SocialLoginButton({
    super.key,
    required this.text,
    required this.logoAsset,
    required this.backgroundColor,
    this.textColor = Colors.black, // 기본 텍스트 색상
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 500),
        child: ElevatedButton(
          onPressed: onPressed,
          style: ButtonStyle(
            backgroundColor: WidgetStateProperty.resolveWith((states) {
              // 마우스 Hover 시 색상을 약간 어둡게 처리하여 시각적 피드백 제공
              if (states.contains(WidgetState.hovered)) {
                return backgroundColor.withValues(alpha: 0.9);
              }
              return backgroundColor;
            }),
            elevation: WidgetStateProperty.resolveWith((states) {
              // Hover 시 그림자 강조 (웹/데스크톱 UX 개선)
              if (states.contains(WidgetState.hovered)) return 4;
              return 1;
            }),
            minimumSize: WidgetStateProperty.all(
              const Size(double.infinity, 48), // 접근성을 위한 최소 터치 영역(48px) 보장
            ),
            shape: WidgetStateProperty.all(
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(8.0)),
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 12.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SvgPicture.asset(
                  logoAsset,
                  height: 18.0, // 로고 크기 고정
                ),
                const SizedBox(width: 8.0),
                Text(
                  text,
                  style: TextStyle(
                    color: textColor,
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}