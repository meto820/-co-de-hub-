from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import os, json

app = Flask(__name__)
app.secret_key = "gizli_anahtar"

DATA_KLASORU = "data"
LOG_DOSYASI = os.path.join(DATA_KLASORU, "log.txt")
KULLANICI_DOSYASI = os.path.join(DATA_KLASORU, "kullanicilar.json")

os.makedirs(DATA_KLASORU, exist_ok=True)
if not os.path.exists(LOG_DOSYASI):
    with open(LOG_DOSYASI, "w", encoding="utf-8") as f:
        f.write("=== LOG SIFIRLANDI ===\n")
if not os.path.exists(KULLANICI_DOSYASI):
    with open(KULLANICI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({}, f)

def kullanicilari_yukle():
    try:
        with open(KULLANICI_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def kullanicilari_kaydet(veri):
    with open(KULLANICI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, indent=4, ensure_ascii=False)

def log_ekle(kullanici, olay):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    veri = kullanicilari_yukle()
    if kullanici in veri:
        veri[kullanici].setdefault("loglar", []).append({"zaman": zaman, "olay": olay})
        kullanicilari_kaydet(veri)
    with open(LOG_DOSYASI, "a", encoding="utf-8") as f:
        f.write(f"{zaman} - {kullanici} - {olay}\n")

@app.route("/")
def index():
    ad = session.get("kullanici")
    veri = kullanicilari_yukle()
    admin_mi = veri.get(ad, {}).get("admin", False) if ad else False
    return render_template("index.html", admin_mi=admin_mi)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ad = request.form["username"]
        sifre = request.form["password"]
        veri = kullanicilari_yukle()
        if ad in veri and veri[ad]["sifre"] == sifre:
            session["kullanici"] = ad
            log_ekle(ad, "Giriş yapıldı")
            return redirect("/welcome")
        else:
            log_ekle(ad, "Hatalı giriş denemesi")
            return render_template("login.html", hata="Hatalı kullanıcı adı veya şifre.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    if "kullanici" in session:
        log_ekle(session["kullanici"], "Çıkış yapıldı")
    session.pop("kullanici", None)
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        ad = request.form["username"]
        sifre = request.form["password"]
        veri = kullanicilari_yukle()
        if ad in veri:
            return render_template("register.html", hata="Bu kullanıcı zaten var.")
        veri[ad] = {
            "sifre": sifre,
            "admin": ad == "mete",
            "girisler": [],
            "kayit_tarihi": datetime.now().strftime("%Y-%m-%d"),
            "paylasimlar": [],
            "loglar": []
        }
        kullanicilari_kaydet(veri)
        session["kullanici"] = ad
        log_ekle(ad, "Kayıt oluşturuldu")
        return redirect("/welcome")
    return render_template("register.html")

@app.route("/welcome")
def welcome():
    if "kullanici" not in session:
        return redirect("/login")
    ad = session["kullanici"]
    veri = kullanicilari_yukle()
    admin_mi = veri.get(ad, {}).get("admin", False)
    return render_template("welcome.html", username=ad, admin_mi=admin_mi)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    ad = session.get("kullanici")
    veri = kullanicilari_yukle()
    if not ad or not veri.get(ad, {}).get("admin"):
        return redirect("/")

    mesaj = ""
    if request.method == "POST":
        yeni_admin = request.form.get("yeni_admin")
        if yeni_admin in veri:
            veri[yeni_admin]["admin"] = True
            kullanicilari_kaydet(veri)
            mesaj = f"{yeni_admin} artık bir admin!"
        else:
            mesaj = "Kullanıcı bulunamadı."

    grafik_verisi = {
        isim: len(kullanici.get("girisler", []))
        for isim, kullanici in veri.items()
    }
    toplam_kullanici = len(veri)
    toplam_giris = sum(len(kullanici.get("girisler", [])) for kullanici in veri.values())

    return render_template("admin.html", veri=grafik_verisi, toplam=toplam_kullanici,
                           giris_sayisi=toplam_giris, mesaj=mesaj, kullanicilar=veri)

@app.route("/profile")
def profile():
    if "kullanici" not in session:
        return redirect("/login")
    ad = session["kullanici"]
    veri = kullanicilari_yukle()
    admin_mi = veri.get(ad, {}).get("admin", False)
    return render_template("profile.html", username=ad, kayit=veri[ad]["kayit_tarihi"],
                           girisler=veri[ad]["girisler"], paylasimlar=veri[ad]["paylasimlar"],
                           admin_mi=admin_mi)

@app.route("/share", methods=["GET", "POST"])
def share():
    if "kullanici" not in session:
        return redirect("/login")
    ad = session["kullanici"]
    veri = kullanicilari_yukle()
    admin_mi = veri.get(ad, {}).get("admin", False)

    if request.method == "POST":
        kod = request.form["kod"]
        etiket = request.form["etiket"]
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
        veri[ad]["paylasimlar"].append({"kod": kod, "etiket": etiket, "zaman": zaman})
        kullanicilari_kaydet(veri)
        log_ekle(ad, f"Yeni paylaşım: {etiket}")
        return render_template("share.html", basarili="Kod başarıyla paylaşıldı!", admin_mi=admin_mi)

    return render_template("share.html", admin_mi=admin_mi)

@app.route("/delete_share", methods=["POST"])
def delete_share():
    if "kullanici" not in session:
        return redirect("/login")

    aktif = session["kullanici"]
    hedef = request.form.get("hedef_kullanici")
    try:
        index = int(request.form.get("index"))
    except:
        return "Geçersiz index", 400

    veri = kullanicilari_yukle()
    if aktif != hedef and not veri.get(aktif, {}).get("admin"):
        return "Yetkisiz işlem", 403
    if hedef not in veri or index >= len(veri[hedef]["paylasimlar"]):
        return "Paylaşım bulunamadı", 404

    etiket = veri[hedef]["paylasimlar"][index].get("etiket", "Bilinmeyen")
    del veri[hedef]["paylasimlar"][index]
    kullanicilari_kaydet(veri)
    log_ekle(aktif, f"{hedef} paylaşımı silindi: {etiket}")
    return redirect("/profile" if aktif == hedef else "/admin")

@app.route("/delete_user", methods=["POST"])
def delete_user():
    if "kullanici" not in session:
        return redirect("/login")

    aktif = session["kullanici"]
    hedef = request.form.get("hedef_kullanici")
    veri = kullanicilari_yukle()

    if aktif != hedef and not veri.get(aktif, {}).get("admin"):
        return "Yetkisiz işlem", 403
    if hedef not in veri:
        return "Kullanıcı bulunamadı", 404

    del veri[hedef]
    kullanicilari_kaydet(veri)
    log_ekle(aktif, f"{hedef} adlı kullanıcı silindi")

    if aktif == hedef:
        session.pop("kullanici", None)
        return redirect("/")
    else:
        return redirect("/admin")
if __name__ == "__main__":
    print("Flask uygulaması başlatılıyor...")
    app.run(debug=True)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port

