import os
import markdown


class ExportController:
    HAS_EXPORT_LIBS = False

    try:
        from fpdf import FPDF
        from docx import Document
        HAS_EXPORT_LIBS = True
    except ImportError:
        pass

    @staticmethod
    def export_pdf(file_path, markdown_text):
        try:
            import re
            from fpdf import FPDF
            
            if not file_path:
                return False, "文件路径为空"
            
            if not markdown_text:
                return False, "内容为空"

            pdf = FPDF()
            pdf.add_page()

            font_path = 'C:/Windows/Fonts/simhei.ttf'
            code_font_path = 'C:/Windows/Fonts/consola.ttf'

            font_regular = 'Arial'
            font_bold = 'Arial'

            if os.path.exists(font_path):
                pdf.add_font('SimHei', '', font_path)
                pdf.add_font('SimHei', 'B', font_path)
                font_regular = 'SimHei'
                font_bold = 'SimHei'

            lines = markdown_text.split('\n')
            in_code_block = False
            
            for line in lines:
                if line is None:
                    continue
                    
                line = str(line)
                
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                
                if in_code_block:
                    pdf.set_font(font_regular, '', 10)
                    pdf.cell(0, 5, line)
                    pdf.ln()
                elif line.startswith('# ') and len(line) > 2:
                    pdf.set_font(font_bold, 'B', 20)
                    pdf.cell(0, 12, line[2:])
                    pdf.ln()
                elif line.startswith('## ') and len(line) > 3:
                    pdf.set_font(font_bold, 'B', 16)
                    pdf.cell(0, 10, line[3:])
                    pdf.ln()
                elif line.startswith('### ') and len(line) > 4:
                    pdf.set_font(font_bold, 'B', 14)
                    pdf.cell(0, 8, line[4:])
                    pdf.ln()
                elif line.startswith('- ') and len(line) > 2:
                    pdf.set_font(font_regular, '', 12)
                    pdf.cell(0, 6, f"  - {line[2:]}")
                    pdf.ln()
                elif line.startswith('* ') and len(line) > 2:
                    pdf.set_font(font_regular, '', 12)
                    pdf.cell(0, 6, f"  - {line[2:]}")
                    pdf.ln()
                elif re.match(r'^\d+\.\s', line):
                    match = re.match(r'^(\d+)\.\s(.*)', line)
                    if match:
                        pdf.set_font(font_regular, '', 12)
                        pdf.cell(0, 6, f"  {match.group(1)}. {match.group(2)}")
                        pdf.ln()
                    else:
                        pdf.set_font(font_regular, '', 12)
                        pdf.cell(0, 6, line)
                        pdf.ln()
                elif line.startswith('>'):
                    pdf.set_font(font_regular, '', 11)
                    pdf.cell(0, 5, line[1:])
                    pdf.ln()
                elif line.strip() == '':
                    pdf.ln(3)
                else:
                    pdf.set_font(font_regular, '', 12)
                    pdf.cell(0, 6, line)
                    pdf.ln()

            pdf.output(file_path)
            return True, f"PDF 已成功导出到:\n{file_path}"
        except ImportError:
            return False, "fpdf2 库未安装，请运行: pip install fpdf2"
        except Exception as e:
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            print(f"PDF导出错误详情: {error_details}")
            return False, f"导出 PDF 时出错:\n{type(e).__name__}: {str(e)}"

    @staticmethod
    def export_word(file_path, markdown_text):
        if not ExportController.HAS_EXPORT_LIBS:
            return False, "python-docx 库未安装，请运行: pip install python-docx"
        
        try:
            from docx import Document
            doc = Document()
            for line in markdown_text.split('\n'):
                if line.startswith('# '):
                    doc.add_heading(line[2:], level=1)
                elif line.startswith('## '):
                    doc.add_heading(line[3:], level=2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:], level=3)
                else:
                    if line.strip():
                        doc.add_paragraph(line)
            doc.save(file_path)
            return True, f"Word 文档已成功导出到:\n{file_path}"
        except Exception as e:
            return False, f"导出 Word 文档时出错:\n{str(e)}"

    @staticmethod
    def export_html(file_path, markdown_text):
        try:
            html = markdown.markdown(markdown_text, extensions=['fenced_code'])
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"<!doctype html><meta charset='utf-8'><body>{html}</body>")
            return True, f"HTML 文件已成功导出到:\n{file_path}"
        except Exception as e:
            return False, f"导出 HTML 文件时出错:\n{str(e)}"
