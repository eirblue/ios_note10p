/* v78 private artifact transport; Node builtins only. No Image interpretation. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const BASE = path.resolve(__dirname, '../private');
const MAX = 256 * 1024 * 1024;
const MAGIC = Buffer.from('N10SEAL1');
function check(ok) { if (!ok) throw new Error('sealed artifact contract'); }
function below(file) {
  const target = path.resolve(file);
  check(target.startsWith(BASE + path.sep));
  return target;
}
function target(file) {
  const out = below(file);
  check(fs.realpathSync(BASE) === BASE && fs.realpathSync(path.dirname(out)) === path.dirname(out));
  check(!fs.existsSync(out));
  return out;
}
function read(file, bound) {
  const input = below(file), before = fs.lstatSync(input);
  check(before.isFile() && !before.isSymbolicLink() && fs.realpathSync(input) === input);
  check(before.size > 0 && before.size <= bound);
  const data = fs.readFileSync(input), after = fs.lstatSync(input);
  check(data.length === before.size && before.size === after.size && before.ino === after.ino && before.mtimeMs === after.mtimeMs);
  return data;
}
function publish(out, data) {
  const temporary = path.join(path.dirname(out), '.v78-sealed-' + crypto.randomUUID());
  let fd;
  try {
    fd = fs.openSync(temporary, 'wx', 0o600);
    fs.writeFileSync(fd, data); fs.fsyncSync(fd); fs.closeSync(fd); fd = undefined;
    // Exclusive atomic publication. Existing paths are never replaced.
    fs.linkSync(temporary, out);
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}
function fingerprint(key) {
  return crypto.createHash('sha256').update(key.export({type:'spki', format:'der'})).digest('hex');
}
function publicKey(encoded) {
  check(typeof encoded === 'string' && encoded.length <= 8192);
  const bytes = Buffer.from(encoded, 'base64');
  check(bytes.toString('base64') === encoded);
  const pem = bytes.toString('ascii');
  check(pem.startsWith('-----BEGIN PUBLIC KEY-----\n') && pem.endsWith('-----END PUBLIC KEY-----\n') && !pem.includes('PRIVATE KEY'));
  const key = crypto.createPublicKey({key:bytes,format:'pem',type:'spki'});
  check(key.asymmetricKeyType === 'rsa' && key.asymmetricKeyDetails.modulusLength === 3072);
  return key;
}
function source(value) { check(/^[0-9a-f]{40}$/.test(value)); return value; }
function base64(value, size) {
  check(typeof value === 'string');
  const bytes = Buffer.from(value, 'base64');
  check(bytes.length === size && bytes.toString('base64') === value);
  return bytes;
}
function keygen(directory) {
  const out = target(directory);
  fs.mkdirSync(out, {mode:0o700});
  const pair = crypto.generateKeyPairSync('rsa', {modulusLength:3072, publicExponent:0x10001});
  fs.writeFileSync(path.join(out, 'private-key.pem'), pair.privateKey.export({type:'pkcs8', format:'pem'}), {flag:'wx',mode:0o600});
  const pem = pair.publicKey.export({type:'spki', format:'pem'});
  fs.writeFileSync(path.join(out, 'recipient-public.pem'), pem, {flag:'wx',mode:0o600});
  return {recipient_public_key_b64:Buffer.from(pem).toString('base64'), recipient_sha256:fingerprint(pair.publicKey)};
}
function seal(input, output, commit) {
  commit = source(commit);
  const out = target(output), key = publicKey(process.env.N10_RECIPIENT_PUBLIC_KEY_B64);
  const plaintext = read(input, MAX), secret = crypto.randomBytes(32), iv = crypto.randomBytes(12);
  const wrapped = crypto.publicEncrypt({key, padding:crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash:'sha256'}, secret);
  const header = Buffer.from(JSON.stringify({v:1, source_commit:commit, recipient_sha256:fingerprint(key),
    plaintext_bytes:plaintext.length, wrapped_key:wrapped.toString('base64'), iv:iv.toString('base64')}));
  check(header.length <= 4096);
  const length = Buffer.alloc(4); length.writeUInt32BE(header.length);
  const aad = Buffer.concat([MAGIC, length, header]);
  const cipher = crypto.createCipheriv('aes-256-gcm', secret, iv, {authTagLength:16});
  cipher.setAAD(aad);
  const encrypted = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const envelope = Buffer.concat([aad, encrypted, cipher.getAuthTag()]);
  publish(out, envelope);
  secret.fill(0);
  return {sealed:true, source_commit:commit, recipient_sha256:fingerprint(key), ciphertext_bytes:envelope.length};
}
function open(input, privateFile, output, commit) {
  commit = source(commit);
  const out = target(output), envelope = read(input, MAX+8192);
  check(envelope.length >= 12+16 && envelope.subarray(0,8).equals(MAGIC));
  const length = envelope.readUInt32BE(8);
  check(length > 0 && length <= 4096 && 12+length+16 <= envelope.length);
  const headerBytes = envelope.subarray(12,12+length), header = JSON.parse(headerBytes.toString('utf8'));
  check(Buffer.from(JSON.stringify(header)).equals(headerBytes));
  check(Object.keys(header).join(',') === 'v,source_commit,recipient_sha256,plaintext_bytes,wrapped_key,iv');
  check(header.v === 1 && header.source_commit === commit && /^[0-9a-f]{64}$/.test(header.recipient_sha256));
  check(Number.isSafeInteger(header.plaintext_bytes) && header.plaintext_bytes > 0 && header.plaintext_bytes <= MAX);
  check(envelope.length === 12+length+header.plaintext_bytes+16);
  const privateKey = crypto.createPrivateKey(read(privateFile, 16384));
  check(privateKey.asymmetricKeyType === 'rsa' && privateKey.asymmetricKeyDetails.modulusLength === 3072);
  check(fingerprint(crypto.createPublicKey(privateKey)) === header.recipient_sha256);
  const secret = crypto.privateDecrypt({key:privateKey,padding:crypto.constants.RSA_PKCS1_OAEP_PADDING,oaepHash:'sha256'}, base64(header.wrapped_key,384));
  check(secret.length === 32);
  const decipher = crypto.createDecipheriv('aes-256-gcm', secret, base64(header.iv,12), {authTagLength:16});
  decipher.setAAD(envelope.subarray(0,12+length));
  decipher.setAuthTag(envelope.subarray(envelope.length-16));
  // Keep plaintext in memory until authentication succeeds; no wrong-key/tamper file.
  const plaintext = Buffer.concat([decipher.update(envelope.subarray(12+length,envelope.length-16)), decipher.final()]);
  check(plaintext.length === header.plaintext_bytes);
  publish(out, plaintext);
  secret.fill(0);
  return {authenticated:true, source_commit:commit, recipient_sha256:header.recipient_sha256};
}
try {
  const args = process.argv.slice(2);
  let result;
  if (args[0] === 'keygen' && args.length === 2) result = keygen(args[1]);
  else if (args[0] === 'recipient' && args.length === 1) result = {recipient_sha256:fingerprint(publicKey(process.env.N10_RECIPIENT_PUBLIC_KEY_B64))};
  else if (args[0] === 'seal' && args.length === 4) result = seal(args[1],args[2],args[3]);
  else if (args[0] === 'open' && args.length === 5) result = open(args[1],args[2],args[3],args[4]);
  else throw new Error('fixed transport command');
  process.stdout.write(JSON.stringify(result)+'\n');
} catch (_) {
  process.stderr.write('sealed affinity artifact rejected\n'); process.exitCode = 1;
}
