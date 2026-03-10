// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_context.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserContext _$UserContextFromJson(Map<String, dynamic> json) => UserContext(
  personaState: PersonaState.fromJson(
    json['persona_state'] as Map<String, dynamic>,
  ),
  userProfile: json['user_profile'] as Map<String, dynamic>,
  userTitle: json['user_title'] as String,
);

Map<String, dynamic> _$UserContextToJson(UserContext instance) =>
    <String, dynamic>{
      'persona_state': instance.personaState,
      'user_profile': instance.userProfile,
      'user_title': instance.userTitle,
    };

PersonaState _$PersonaStateFromJson(Map<String, dynamic> json) => PersonaState(
  axisPlayful: (json['axis_playful'] as num).toDouble(),
  axisFeisty: (json['axis_feisty'] as num).toDouble(),
  axisDependent: (json['axis_dependent'] as num).toDouble(),
  axisCaregive: (json['axis_caregive'] as num).toDouble(),
  axisReflective: (json['axis_reflective'] as num).toDouble(),
);

Map<String, dynamic> _$PersonaStateToJson(PersonaState instance) =>
    <String, dynamic>{
      'axis_playful': instance.axisPlayful,
      'axis_feisty': instance.axisFeisty,
      'axis_dependent': instance.axisDependent,
      'axis_caregive': instance.axisCaregive,
      'axis_reflective': instance.axisReflective,
    };
