import 'dart:typed_data';

import 'package:bs58check/bs58check.dart' as bs58check;
import 'package:coinslib/bech32/bech32.dart';

import 'bigcoin_network.dart';

/// Converts a Big Coin address into its output script (scriptPubKey) bytes.
///
/// coinslib's own `addressToOutputScript` can't be used here: its SegWit
/// decoder hard-codes the set of allowed bech32 prefixes (`bc`, `tb`, ...) and
/// rejects Big Coin's custom `big` / `tbig` HRPs on decode. So we decode the
/// address ourselves using the underlying (HRP-agnostic) bech32 codec and the
/// base58check codec, then assemble the standard scripts:
///
///   P2WPKH  ->  OP_0 <20-byte program>
///   P2WSH   ->  OP_0 <32-byte program>
///   P2PKH   ->  OP_DUP OP_HASH160 <20> OP_EQUALVERIFY OP_CHECKSIG
///   P2SH    ->  OP_HASH160 <20> OP_EQUAL
class AddressScript {
  /// Returns the scriptPubKey for [address] on [network], or throws
  /// [FormatException] if the address is invalid for this network.
  static Uint8List forAddress(String address, BigCoinNetwork network) {
    final net = network.coins;
    final addr = address.trim();

    // Try base58check (legacy P2PKH / P2SH) first.
    Uint8List? b58;
    try {
      b58 = bs58check.decode(addr);
    } catch (_) {}
    if (b58 != null) {
      final version = b58[0];
      final payload = b58.sublist(1);
      if (payload.length != 20) {
        throw FormatException('Bad base58 payload length for $addr');
      }
      if (version == net.pubKeyHash) {
        // OP_DUP OP_HASH160 <20> OP_EQUALVERIFY OP_CHECKSIG
        return Uint8List.fromList(
            [0x76, 0xa9, 0x14, ...payload, 0x88, 0xac]);
      }
      if (version == net.scriptHash) {
        // OP_HASH160 <20> OP_EQUAL
        return Uint8List.fromList([0xa9, 0x14, ...payload, 0x87]);
      }
      throw FormatException('Address version $version is not for ${network.id}');
    }

    // Otherwise treat as bech32 SegWit.
    final Bech32 decoded;
    try {
      decoded = bech32.decode(addr);
    } catch (e) {
      throw FormatException('Not a valid Big Coin address: $addr');
    }
    if (decoded.hrp != net.bech32) {
      throw FormatException(
          'Wrong network: expected "${net.bech32}", got "${decoded.hrp}"');
    }
    if (decoded.data.isEmpty) {
      throw FormatException('Empty witness program in $addr');
    }
    final witnessVersion = decoded.data[0];
    final program = _convertBits(decoded.data.sublist(1), 5, 8, pad: false);
    if (witnessVersion != 0) {
      throw FormatException('Unsupported witness version $witnessVersion');
    }
    if (program.length != 20 && program.length != 32) {
      throw FormatException('Bad witness program length ${program.length}');
    }
    // OP_0 <push program>
    return Uint8List.fromList([0x00, program.length, ...program]);
  }

  /// bech32 5-bit <-> 8-bit regrouping (BIP173). [pad] false for decode.
  static List<int> _convertBits(
    List<int> data,
    int from,
    int to, {
    required bool pad,
  }) {
    var acc = 0;
    var bits = 0;
    final result = <int>[];
    final maxv = (1 << to) - 1;
    for (final value in data) {
      if (value < 0 || (value >> from) != 0) {
        throw const FormatException('Invalid data value in bech32 program');
      }
      acc = (acc << from) | value;
      bits += from;
      while (bits >= to) {
        bits -= to;
        result.add((acc >> bits) & maxv);
      }
    }
    if (pad) {
      if (bits > 0) result.add((acc << (to - bits)) & maxv);
    } else if (bits >= from || ((acc << (to - bits)) & maxv) != 0) {
      throw const FormatException('Invalid padding in bech32 program');
    }
    return result;
  }
}
