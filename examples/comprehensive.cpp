int comprehensive(int n) {
    int total = 0;
    int i = 0;

    // Test while loop and nested if-else
    while (i < n) {
        if (i > 2 && i < 8) {
            total = total + i;
        } else {
            total = total + 1;
        }
        i++;
    }

    // Test for loop
    for (int j = 0; j < 5; j++) {
        total = total + j;
    }

    // Test do-while loop
    do {
        total = total - 1;
    } while (total > 20);

    // Test composite OR condition
    if (total < 0 || total == 10) {
        total = 0;
    }

    return total;
}
