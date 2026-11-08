# Kiểm tra bảo mật

Ngày 09/11/2026, bản v1.0.1.

- Windows Defender quét EXE và không phát hiện mối đe dọa.
- pip-audit kiểm tra các gói khóa trong requirements.txt và requirements-dev.txt, không báo lỗ hổng đã biết.
- Rà mã ứng dụng không tìm thấy hành vi tải/chạy mã từ Internet, thu thập thông tin đăng nhập hay đăng ký tự khởi động.
- 22 kiểm thử đạt.

EXE chưa có chữ ký Authenticode. Các kiểm tra này có giới hạn và không bảo đảm tuyệt đối không có mã độc hoặc lỗ hổng. pip-audit không thay thế kiểm toán toàn bộ thư viện native Qt và Python.

## Xác minh bản tải

Tải DesktopCat.exe và SHA256SUMS.txt từ Release chính thức. Chạy Get-FileHash .\DesktopCat.exe -Algorithm SHA256 trong PowerShell và so sánh kết quả với SHA256SUMS.txt. SHA-256 phát hiện thay đổi so với file đã phát hành.

## Cập nhật Release

Push mã nguồn chỉ cập nhật repository. Mỗi lần sửa ảnh hoặc mã cần build EXE, quét file mới, tạo SHA256SUMS.txt mới và đăng Release mới kèm hai file. Đánh dấu Release là latest để nút tải README nhận đúng EXE.
