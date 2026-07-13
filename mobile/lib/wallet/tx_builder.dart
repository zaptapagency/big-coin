import 'dart:typed_data';

import 'package:coinslib/coinslib.dart';
import 'package:hex/hex.dart';

import '../models/chain_models.dart';
import 'address_script.dart';
import 'bigcoin_network.dart';

/// A signed, ready-to-broadcast transaction.
class SignedTx {
  final String rawHex;
  final String txid;
  final int feeSats;
  final int changeSats;
  final int amountSats;
  final List<Utxo> inputs;

  const SignedTx({
    required this.rawHex,
    required this.txid,
    required this.feeSats,
    required this.changeSats,
    required this.amountSats,
    required this.inputs,
  });
}

class InsufficientFundsException implements Exception {
  final int neededSats;
  final int availableSats;
  InsufficientFundsException(this.neededSats, this.availableSats);
  @override
  String toString() =>
      'InsufficientFundsException: need $neededSats sats, have $availableSats';
}

/// Builds and signs Big Coin P2WPKH (native SegWit) spends entirely on-device.
///
/// Coin selection is a simple largest-first accumulation with iterative fee
/// estimation. All UTXOs are assumed to belong to a single key ([wif]) — the
/// wallet currently derives one receive address, so that holds. Nothing here
/// touches the network; the caller broadcasts the resulting [SignedTx.rawHex].
class TxBuilder {
  final BigCoinNetwork network;

  TxBuilder(this.network);

  // Virtual-size constants for P2WPKH (vbytes). Slightly rounded up so our fee
  // is never short of the node's own vsize calculation.
  static const int _vbOverhead = 11; // version+locktime+segwit marker+counts
  static const int _vbPerInput = 68; // outpoint+sequence+witness(sig+pubkey)/4
  static const int _vbPerOutput = 31; // value + P2WPKH scriptPubKey

  /// Dust threshold for a P2WPKH output (sats). Change below this is dropped
  /// into the fee instead of creating an unspendable output.
  static const int dustSats = 294;

  int _estimateVsize(int nIn, int nOut) =>
      _vbOverhead + _vbPerInput * nIn + _vbPerOutput * nOut;

  /// Selects inputs and builds a signed transaction paying [amountSats] to
  /// [toAddress], with change returned to [changeAddress].
  ///
  /// [feeRateSatPerVByte] is the fee rate in sats/vByte (convert a BIG/kB rate
  /// with `feeRateBigPerKb * 1e8 / 1000`).
  SignedTx buildSpend({
    required List<Utxo> utxos,
    required String toAddress,
    required int amountSats,
    required String changeAddress,
    required String wif,
    required double feeRateSatPerVByte,
  }) {
    if (amountSats <= 0) {
      throw ArgumentError('amount must be positive');
    }
    final feeRate = feeRateSatPerVByte <= 0 ? 1.0 : feeRateSatPerVByte;

    // Largest-first: fewest inputs, lowest fee.
    final sorted = [...utxos]..sort((a, b) => b.amountSats - a.amountSats);
    final available = sorted.fold<int>(0, (s, u) => s + u.amountSats);

    final selected = <Utxo>[];
    int selectedSats = 0;
    int fee = 0;
    int change = 0;
    bool withChange = true;

    for (final u in sorted) {
      selected.add(u);
      selectedSats += u.amountSats;

      // Try WITH a change output first.
      int vsize = _estimateVsize(selected.length, 2);
      fee = (vsize * feeRate).ceil();
      change = selectedSats - amountSats - fee;

      if (change >= dustSats) {
        withChange = true;
        break;
      }
      if (change >= 0) {
        // Change would be dust: drop it, fold into fee, recompute for 1 output.
        vsize = _estimateVsize(selected.length, 1);
        final feeNoChange = (vsize * feeRate).ceil();
        if (selectedSats - amountSats >= feeNoChange) {
          fee = selectedSats - amountSats; // no change: remainder is the fee
          change = 0;
          withChange = false;
          break;
        }
      }
      // Not enough yet; add another input.
      withChange = false;
    }

    final covers = withChange
        ? selectedSats >= amountSats + fee + dustSats ||
            selectedSats - amountSats - fee >= dustSats
        : selectedSats - amountSats >= fee;
    if (!covers || selectedSats < amountSats) {
      final need = amountSats + (fee > 0 ? fee : _estimateVsize(1, 2));
      throw InsufficientFundsException(need, available);
    }

    final builder = TransactionBuilder(network: network.coins);
    builder.setVersion(2);
    for (final u in selected) {
      builder.addInput(
        u.txid,
        u.vout,
        null,
        Uint8List.fromList(HEX.decode(u.scriptPubKey)),
      );
    }
    builder.addOutput(
      AddressScript.forAddress(toAddress, network),
      BigInt.from(amountSats),
    );
    if (withChange && change >= dustSats) {
      builder.addOutput(
        AddressScript.forAddress(changeAddress, network),
        BigInt.from(change),
      );
    } else {
      change = 0;
    }

    final keyPair = ECPair.fromWIF(wif, network: network.coins);
    for (var i = 0; i < selected.length; i++) {
      builder.sign(
        vin: i,
        keyPair: keyPair,
        witnessValue: BigInt.from(selected[i].amountSats),
      );
    }

    final tx = builder.build();
    return SignedTx(
      rawHex: tx.toHex(),
      txid: tx.getId(),
      feeSats: fee,
      changeSats: change,
      amountSats: amountSats,
      inputs: selected,
    );
  }
}
