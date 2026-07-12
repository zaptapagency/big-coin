import 'package:json_annotation/json_annotation.dart';

part 'wallet_model.g.dart';

@JsonSerializable(fieldRename: FieldRename.snake)
class Address {
  final String address;
  final String pubkeyHash;

  Address({
    required this.address,
    required this.pubkeyHash,
  });

  factory Address.fromJson(Map<String, dynamic> json) =>
      _$AddressFromJson(json);

  Map<String, dynamic> toJson() => _$AddressToJson(this);
}

@JsonSerializable(fieldRename: FieldRename.snake)
class Balance {
  final double balanceCoins;
  final int balanceCents;

  Balance({
    required this.balanceCoins,
    required this.balanceCents,
  });

  factory Balance.fromJson(Map<String, dynamic> json) =>
      _$BalanceFromJson(json);

  Map<String, dynamic> toJson() => _$BalanceToJson(this);

  @override
  String toString() =>
      '${balanceCoins.toStringAsFixed(8)} BigCoin ($balanceCents cents)';
}

@JsonSerializable(fieldRename: FieldRename.snake)
class BlockchainInfo {
  final int height;
  final String tipHash;
  final double totalMoneyCoins;
  final int totalMoneyCents;
  final int txCount;

  BlockchainInfo({
    required this.height,
    required this.tipHash,
    required this.totalMoneyCoins,
    required this.totalMoneyCents,
    required this.txCount,
  });

  factory BlockchainInfo.fromJson(Map<String, dynamic> json) =>
      _$BlockchainInfoFromJson(json);

  Map<String, dynamic> toJson() => _$BlockchainInfoToJson(this);
}

@JsonSerializable(fieldRename: FieldRename.snake)
class MiningStatus {
  final bool isMining;
  final int blocksMined;
  final int blocksToMine;
  final int currentHeight;

  MiningStatus({
    required this.isMining,
    required this.blocksMined,
    required this.blocksToMine,
    required this.currentHeight,
  });

  factory MiningStatus.fromJson(Map<String, dynamic> json) =>
      _$MiningStatusFromJson(json);

  Map<String, dynamic> toJson() => _$MiningStatusToJson(this);
}
