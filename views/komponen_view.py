"""
komponen_view.py
View — komponen kecil yang dipakai ulang: gaya CSS peta, chip pion, dan tanda ruangan.
Menerima data siap tampil, tanpa logika.
"""

# MARK: - Gaya

CSS = """
<style>
.peta {display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; max-width: 560px;}
.ruang {border: 1px solid rgba(128,128,128,.45); border-radius: 8px; padding: 8px; min-height: 118px;
        font-size: 0.82rem; line-height: 1.35; background: rgba(128,128,128,.06);}
.ruang.aktif {outline: 3px solid #2f6fd6; outline-offset: -2px;}
.ruang .nama {font-weight: 700; font-size: 0.9rem; margin-bottom: 4px;}
.chip {display: inline-block; color: #fff; border-radius: 10px; padding: 0 7px; margin: 1px 2px 1px 0;
       font-size: 0.75rem; font-weight: 700;}
.tag {display: inline-block; border: 1px solid rgba(128,128,128,.6); border-radius: 6px; padding: 0 5px;
      margin: 1px 2px 1px 0; font-size: 0.72rem;}
.ket {opacity: .75; font-size: 0.75rem;}
</style>
"""


# MARK: - Komponen

def chip(label, warna):
    return f'<span class="chip" style="background:{warna}">{label}</span>'


def tanda(teks):
    return f'<span class="tag">{teks}</span>'


def peta_html(sel):
    """Peta 3×3 dari isi kotak yang disiapkan PermainanViewModel.sel_peta()."""
    kotak = []
    for s in sel:
        isi = [f'<div class="nama">{s["nama"]}</div>']
        if s['pion']:
            isi.append(''.join(chip(label, warna) for label, warna in s['pion']) + '<br>')
        if s['tag']:
            isi.append(''.join(tanda(t) for t in s['tag']) + '<br>')
        if s['orang']:
            isi.append(f'<span class="ket">{", ".join(s["orang"])}</span>')
        kelas = 'ruang aktif' if s['aktif'] else 'ruang'
        kotak.append(f'<div class="{kelas}">{"".join(isi)}</div>')
    return CSS + f'<div class="peta">{"".join(kotak)}</div>'
