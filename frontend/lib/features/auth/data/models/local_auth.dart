import 'package:json_annotation/json_annotation.dart';

part 'local_auth.g.dart';

@JsonSerializable()
class LocalRegisterRequest {
  final String email;
  final String password;

  LocalRegisterRequest({
    required this.email,
    required this.password,
  });

  factory LocalRegisterRequest.fromJson(Map<String, dynamic> json) =>
      _$LocalRegisterRequestFromJson(json);
  Map<String, dynamic> toJson() => _$LocalRegisterRequestToJson(this);
}

@JsonSerializable()
class LocalLoginRequest {
  final String email;
  final String password;

  LocalLoginRequest({
    required this.email,
    required this.password,
  });

  factory LocalLoginRequest.fromJson(Map<String, dynamic> json) =>
      _$LocalLoginRequestFromJson(json);
  Map<String, dynamic> toJson() => _$LocalLoginRequestToJson(this);
}
