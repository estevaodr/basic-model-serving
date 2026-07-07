def test_predict_upload_returns_five_predictions(client, sample_jpeg_bytes):
    response = client.post(
        "/predict",
        files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    payload = response.json()
    predictions = payload["predictions"]
    assert len(predictions) == 5

    for item in predictions:
        assert isinstance(item["label"], str)
        assert isinstance(item["confidence"], float)
        assert 0 <= item["confidence"] <= 1
