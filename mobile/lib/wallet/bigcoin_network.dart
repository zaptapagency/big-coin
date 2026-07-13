import 'package:coinslib/coinslib.dart';

/// Big Coin (BIG) network parameters.
///
/// Values mirror the C++ chain's `src/chainparams.cpp`:
///   mainnet: PUBKEY_ADDRESS=25, SCRIPT_ADDRESS=5, SECRET_KEY=176,
///            EXT_PUBLIC_KEY=0x0488B21E, EXT_SECRET_KEY=0x0488ADE4, bech32 "big"
///   testnet: PUBKEY_ADDRESS=111, SCRIPT_ADDRESS=196, SECRET_KEY=239,
///            EXT_PUBLIC_KEY=0x043587CF, EXT_SECRET_KEY=0x04358394, bech32 "tbig"
///
/// These make the wallet's derived addresses and WIFs recognisable by
/// `bigcoind` (validateaddress / importprivkey) on the respective network.
class BigCoinNetwork {
  final String id; // "mainnet" | "testnet"
  final NetworkType coins; // coinslib NetworkType
  final String addressPrefixHint; // human hint, e.g. "big1…" / "tbig1…"

  const BigCoinNetwork({
    required this.id,
    required this.coins,
    required this.addressPrefixHint,
  });

  bool get isTestnet => id == 'testnet';

  static final NetworkType _mainnetCoins = NetworkType(
    messagePrefix: 'BigCoin Signed Message:\n',
    bech32: 'big',
    bip32: Bip32Type(public: 0x0488b21e, private: 0x0488ade4),
    pubKeyHash: 25,
    scriptHash: 5,
    wif: 176,
    opreturnSize: 80,
  );

  static final NetworkType _testnetCoins = NetworkType(
    messagePrefix: 'BigCoin Signed Message:\n',
    bech32: 'tbig',
    bip32: Bip32Type(public: 0x043587cf, private: 0x04358394),
    pubKeyHash: 111,
    scriptHash: 196,
    wif: 239,
    opreturnSize: 80,
  );

  static final BigCoinNetwork mainnet = BigCoinNetwork(
    id: 'mainnet',
    coins: _mainnetCoins,
    addressPrefixHint: 'big1…',
  );

  static final BigCoinNetwork testnet = BigCoinNetwork(
    id: 'testnet',
    coins: _testnetCoins,
    addressPrefixHint: 'tbig1…',
  );

  static BigCoinNetwork byId(String id) =>
      id == 'testnet' ? testnet : mainnet;
}
