from main import euclidean_distance


def test_identical_embeddings_have_zero_distance():
    embedding = [0.1] * 128
    assert euclidean_distance(embedding, embedding) == 0


def test_different_embeddings_have_nonzero_distance():
    assert euclidean_distance([0.0] * 128, [0.1] * 128) > 0.6

