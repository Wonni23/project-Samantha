import 'package:json_annotation/json_annotation.dart';

part 'user_context.g.dart';

@JsonSerializable()
class UserContext {
  @JsonKey(name: 'persona_state')
  final PersonaState personaState;
  @JsonKey(name: 'user_profile')
  final Map<String, dynamic> userProfile;
  @JsonKey(name: 'user_title')
  final String userTitle;

  UserContext({
    required this.personaState,
    required this.userProfile,
    required this.userTitle,
  });

  factory UserContext.fromJson(Map<String, dynamic> json) =>
      _$UserContextFromJson(json);
  Map<String, dynamic> toJson() => _$UserContextToJson(this);
}

@JsonSerializable()
class PersonaState {
  @JsonKey(name: 'axis_playful')
  final double axisPlayful;
  @JsonKey(name: 'axis_feisty')
  final double axisFeisty;
  @JsonKey(name: 'axis_dependent')
  final double axisDependent;
  @JsonKey(name: 'axis_caregive')
  final double axisCaregive;
  @JsonKey(name: 'axis_reflective')
  final double axisReflective;

  PersonaState({
    required this.axisPlayful,
    required this.axisFeisty,
    required this.axisDependent,
    required this.axisCaregive,
    required this.axisReflective,
  });

  factory PersonaState.fromJson(Map<String, dynamic> json) =>
      _$PersonaStateFromJson(json);
  Map<String, dynamic> toJson() => _$PersonaStateToJson(this);
}
