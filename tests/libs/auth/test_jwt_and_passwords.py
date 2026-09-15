"""Tests for libs/auth: JWT round trip and password hashing. No DB or
network needed -- pure logic."""

import uuid

import pytest

from libs.auth.jwt import InvalidTokenError, create_access_token, decode_access_token
from libs.auth.passwords import hash_password, verify_password


def test_jwt_round_trip():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, tenant_id=tenant_id)

    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)


def test_invalid_token_raises():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-real-token")


def test_password_hash_verifies_correct_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)


def test_password_hash_rejects_wrong_password():
    hashed = hash_password("correct horse battery staple")
    assert not verify_password("wrong password", hashed)


def test_password_hash_is_not_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
