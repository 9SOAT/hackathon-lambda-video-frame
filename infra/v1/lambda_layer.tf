# data "archive_file" "ffmpeg_zip" {
#   type        = "zip"
#   source_file = "${path.module}/../build/ffmpeg-layer.zip"  
#   output_path = "${path.module}/../build/ffmpeg-layer.zip"   
# }


# resource "aws_lambda_layer_version" "ffmpeg" {
#   layer_name          = "ffmpeg-layer-${random_id.suffix.hex}"
#   filename            = data.archive_file.ffmpeg_zip.output_path
#   compatible_runtimes = ["python3.9"]
#   source_code_hash    = data.archive_file.ffmpeg_zip.output_base64sha256
# }
