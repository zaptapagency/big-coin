// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'wallet_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Address _$AddressFromJson(Map<String, dynamic> json) => Address(
      address: json['address'] as String,
      pubkeyHash: json['pubkey_hash'] as String,
    );

Map<String, dynamic> _$AddressToJson(Address instance) => <String, dynamic>{
      'address': instance.address,
      'pubkey_hash': instance.pubkeyHash,
    };

Balance _$BalanceFromJson(Map<String, dynamic> json) => Balance(
      balanceCoins: (json['balance_coins'] as num).toDouble(),
      balanceCents: (json['balance_cents'] as num).toInt(),
    );

Map<String, dynamic> _$BalanceToJson(Balance instance) => <String, dynamic>{
      'balance_coins': instance.balanceCoins,
      'balance_cents': instance.balanceCents,
    };

BlockchainInfo _$BlockchainInfoFromJson(Map<String, dynamic> json) =>
    BlockchainInfo(
      height: (json['height'] as num).toInt(),
      tipHash: json['tip_hash'] as String,
      totalMoneyCoins: (json['total_money_coins'] as num).toDouble(),
      totalMoneyCents: (json['total_money_cents'] as num).toInt(),
      txCount: (json['tx_count'] as num).toInt(),
    );

Map<String, dynamic> _$BlockchainInfoToJson(BlockchainInfo instance) =>
    <String, dynamic>{
      'height': instance.height,
      'tip_hash': instance.tipHash,
      'total_money_coins': instance.totalMoneyCoins,
      'total_money_cents': instance.totalMoneyCents,
      'tx_count': instance.txCount,
    };

MiningStatus _$MiningStatusFromJson(Map<String, dynamic> json) => MiningStatus(
      isMining: json['is_mining'] as bool,
      blocksMined: (json['blocks_mined'] as num).toInt(),
      blocksToMine: (json['blocks_to_mine'] as num).toInt(),
      currentHeight: (json['current_height'] as num).toInt(),
    );

Map<String, dynamic> _$MiningStatusToJson(MiningStatus instance) =>
    <String, dynamic>{
      'is_mining': instance.isMining,
      'blocks_mined': instance.blocksMined,
      'blocks_to_mine': instance.blocksToMine,
      'current_height': instance.currentHeight,
    };
