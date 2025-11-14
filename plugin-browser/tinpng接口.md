你看到的现象是因为 TinyPNG 的 resize 接口有两种返回形式，我们之前的代码只按“返回 JSON”处理，结果拿到的是原始（仅压缩未缩放）的图片，所以宽高没变。刚刚我已更新 compressAndResize：
如果 TinyPNG 在响应头里给了 Location，我们直接用该 URL 再去下载；
如果返回 JSON，就从 JSON 里取 output.url；
如果返回的就是二进制图片流，就直接把这个响应体当作最终图片。
也就是说，再次调用时，无论 TinyPNG 采用哪种返回形式都能正确取到缩放后的图片。