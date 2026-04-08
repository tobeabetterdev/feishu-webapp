import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert "工厂订单数据核对API" in response.json()["message"]

def test_get_factory_groups():
    """测试获取工厂集团配置"""
    response = client.get("/api/factory-groups")
    assert response.status_code == 200
    data = response.json()
    assert "hengyi" in data
    assert "xinfengming" in data
