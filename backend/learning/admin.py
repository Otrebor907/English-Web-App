from django.contrib import admin
from .models import (
    Area, Difficolta, Lezione, Livello, Prerequisito, Progresso,
    QuesitoFinale, QuesitoGuidato, StrutturaQuiz, StrutturaLezione, StatoLezione, Tipologia, User,
)


class PrerequisitoInline(admin.TabularInline):
    model = Prerequisito
    fk_name = "lezione"
    extra = 0
    autocomplete_fields = ["richiede_lezione"]


class SezioneInline(admin.TabularInline):
    model = StrutturaLezione
    extra = 0
    fields = ["ordine", "tipo_sezione", "formato_web", "contenuto"]


class QuizInline(admin.TabularInline):
    model = StrutturaQuiz
    extra = 0


@admin.register(Lezione)
class LezioneAdmin(admin.ModelAdmin):
    list_display = ["id", "nome", "area", "livello", "ordine_percorso", "ordine_mvp", "stato"]
    list_filter = ["area", "livello", "stato", "tipologia"]
    search_fields = ["id", "nome", "obiettivo_didattico"]
    ordering = ["ordine_mvp", "ordine_percorso"]
    inlines = [PrerequisitoInline, SezioneInline, QuizInline]


class QuesitoAdminBase(admin.ModelAdmin):
    list_display = ["id", "quiz", "ordine", "tipo"]
    list_filter = ["tipo"]
    search_fields = ["testo", "quiz__lezione__id", "quiz__lezione__nome"]


@admin.register(QuesitoGuidato)
class QuesitoGuidatoAdmin(QuesitoAdminBase):
    pass


@admin.register(QuesitoFinale)
class QuesitoFinaleAdmin(QuesitoAdminBase):
    pass


@admin.register(Progresso)
class ProgressoAdmin(admin.ModelAdmin):
    list_display = ["utente", "lezione", "stato", "punteggio", "completata_il"]
    list_filter = ["stato"]
    search_fields = ["utente__email", "lezione__id", "lezione__nome"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "is_staff", "is_active", "creato_il"]
    list_filter = ["is_staff", "is_active"]
    search_fields = ["email"]
    readonly_fields = ["password", "last_login", "creato_il"]


for model in (Area, Tipologia, Livello, Difficolta, StatoLezione, StrutturaQuiz, StrutturaLezione, Prerequisito):
    admin.site.register(model)
