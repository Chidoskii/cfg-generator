int partialReturn(int x) {
    if (x > 0) {
        return x;
    } else {
        x = x + 1;
    }

    x = x * 2;
    return x;
}