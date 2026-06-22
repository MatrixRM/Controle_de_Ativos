from django import forms
from django.contrib.auth import get_user_model
from .models import Empresa, Equipamento, Manutencao, ItemEstoque, MovimentacaoEstoque

User = get_user_model()


class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        exclude = ['criado_em', 'atualizado_em']
        widgets = {
            'numero_imobilizado': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'empresa': forms.Select(attrs={'class': 'form-control-custom'}),
            'tipo': forms.Select(attrs={'class': 'form-control-custom'}),
            'marca': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'local': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'setor': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Nome do responsável'}),
            'status': forms.Select(attrs={'class': 'form-control-custom'}),
            'sistema_operacional': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'versao_so': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'mac_ethernet': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'AA:BB:CC:DD:EE:FF'}),
            'mac_wifi': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'AA:BB:CC:DD:EE:FF'}),
            'ip': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': '192.168.1.100'}),
            'teamviewer_id': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': '123 456 789'}),
            'versao_office': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'data_aquisicao': forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'}),
            'valor_aquisicao': forms.NumberInput(attrs={'class': 'form-control-custom'}),
            'garantia_ate': forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'}),
            'periodicidade_dias': forms.NumberInput(attrs={'class': 'form-control-custom'}),
            'proxima_manutencao': forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 3}),
        }

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'segmento': forms.Select(attrs={'class': 'form-control-custom'}),
        }


class ManutencaoForm(forms.ModelForm):
    class Meta:
        model = Manutencao
        exclude = ['data_abertura']
        widgets = {
            'equipamento': forms.Select(attrs={'class': 'form-control-custom'}),
            'data_conclusao': forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-control-custom'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 4}),
            'tecnico': forms.Select(attrs={'class': 'form-control-custom'}),
            'custo': forms.NumberInput(attrs={'class': 'form-control-custom'}),
            'status': forms.Select(attrs={'class': 'form-control-custom'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico'].queryset = User.objects.filter(is_active=True)
        self.fields['tecnico'].required = False
        for field_name in ['equipamento', 'tipo', 'status', 'descricao']:
            self.fields[field_name].widget.attrs.pop('required', None)


class ItemEstoqueForm(forms.ModelForm):
    class Meta:
        model = ItemEstoque
        exclude = ['criado_em', 'atualizado_em']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'categoria': forms.Select(attrs={'class': 'form-control-custom'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control-custom'}),
            'quantidade_minima': forms.NumberInput(attrs={'class': 'form-control-custom'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'localizacao': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 3}),
        }


class MovimentacaoEstoqueForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoEstoque
        exclude = ['data', 'responsavel']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control-custom'}),
            'tipo': forms.Select(attrs={'class': 'form-control-custom'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control-custom'}),
            'empresa_origem': forms.Select(attrs={'class': 'form-control-custom'}),
            'empresa_destino': forms.Select(attrs={'class': 'form-control-custom'}),
            'equipamento': forms.Select(attrs={'class': 'form-control-custom'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipamento'].required = False
        self.fields['equipamento'].queryset = Equipamento.objects.all()
        self.fields['empresa_origem'].required = False
        self.fields['empresa_origem'].queryset = Empresa.objects.all()
        self.fields['empresa_destino'].required = False
        self.fields['empresa_destino'].queryset = Empresa.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        quantidade = cleaned_data.get('quantidade')
        item = cleaned_data.get('item')

        if tipo == 'SAIDA' and item and quantidade:
            if quantidade > item.quantidade:
                raise forms.ValidationError(
                    f'Quantidade insuficiente em estoque. Disponível: {item.quantidade} {item.unidade}'
                )

        if tipo == 'TRANSFERENCIA':
            origem = cleaned_data.get('empresa_origem')
            destino = cleaned_data.get('empresa_destino')
            if not origem or not destino:
                raise forms.ValidationError(
                    'Informe a empresa de origem e destino para transferência.'
                )
            if origem == destino:
                raise forms.ValidationError(
                    'A empresa de origem e destino devem ser diferentes.'
                )
        return cleaned_data
