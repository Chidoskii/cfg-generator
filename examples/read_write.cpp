int readWrite(int x) {
    int total = 0;

    cin >> x;

    if (x > 0) {
        total = x * 2;
        cout << total;
    } else {
        total = 0;
        cout << total;
    }

    return total;
}
