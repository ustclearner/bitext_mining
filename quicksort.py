def quicksort(arr):
    """
    快速排序（递归实现）
    时间复杂度：平均 O(n log n)，最坏 O(n²)
    空间复杂度：O(log n)
    """
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quicksort(left) + middle + quicksort(right)


def quicksort_inplace(arr, low=0, high=None):
    """
    快速排序（原地排序，节省内存）
    """
    if high is None:
        high = len(arr) - 1

    if low < high:
        pivot_index = _partition(arr, low, high)
        quicksort_inplace(arr, low, pivot_index - 1)
        quicksort_inplace(arr, pivot_index + 1, high)

    return arr


def _partition(arr, low, high):
    pivot = arr[high]
    i = low - 1

    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]

    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1


if __name__ == "__main__":
    data = [3, 6, 8, 10, 1, 2, 1]
    print("原始数组:", data)
    print("排序结果（新数组）:", quicksort(data))

    data2 = [3, 6, 8, 10, 1, 2, 1]
    print("排序结果（原地）:  ", quicksort_inplace(data2))
