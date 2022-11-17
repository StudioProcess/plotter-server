#!/usr/bin/env bash

# Create self-signed certificate

out="localhost.pem"
domain="localhost"

openssl req -x509 -out $out -keyout $out \
  -newkey rsa:2048 -nodes -sha256 \
  -subj '/CN=localhost/C=AT/L=Vienna/O=Process - Studio for Art and Design OG' -extensions EXT -config <( \
   printf "[dn]\nCN=${domain}\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:${domain}\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth")