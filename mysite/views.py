from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.contrib import messages

from .forms import SuporteForm, BicicletarioRatingForm
from .models import Bicicletario, UserBicicletario, BicicletarioRating


import requests
import folium
from folium.plugins import MarkerCluster
import math






@login_required
def home(request):
    return render(request, 'home.html')

def redirect_to_home(request):
    return redirect(reverse('home'))

def redirect_to_suport(request):
    return redirect(reverse('suporte'))

def suporte(request):
    if request.method == 'POST':
        form = SuporteForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data.get('nome')
            sobrenome = form.cleaned_data.get('sobrenome')
            email = form.cleaned_data.get('email')
            assunto = form.cleaned_data.get('assunto')
            mensagem = form.cleaned_data.get('mensagem')

            mensagem_completa = f'''
                Mensagem recebida abaixo de {email}, {assunto}
                ____________________________

                
                {mensagem}
                '''
            
            send_mail(
                subject='Contato recebido do formulário de suporte',
                message=mensagem_completa,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.NOTIFY_EMAIL],
            )
            messages.add_message(request, messages.SUCCESS, 'Formulário enviado com sucesso!')
    else:
        form = SuporteForm()

    return render(request, 'suporte/suporte.html', {'form': form})

# mapapp/views.py (ou o nome do seu arquivo de views)
# -----------------------------------------------------------------------------
# FUNÇÃO PARA OBTER DADOS DAS ESTAÇÕES DE BICICLETA DA API CITYBIK.ES
# -----------------------------------------------------------------------------
@login_required
def get_actual_bicycle_stations_in_sorocaba(request):
    """
    Busca as estações de bicicleta individuais em Sorocaba através da API CityBik.es.
    """
    all_stations_data = []
    API_BASE_URL = 'http://api.citybik.es/v2/networks'

    print("DEBUG: Iniciando get_actual_bicycle_stations_in_sorocaba()")

    try:
        # 1. Obter todas as redes
        print(f"DEBUG: Buscando todas as redes de {API_BASE_URL}...")
        networks_response = requests.get(API_BASE_URL, timeout=10) # Adiciona timeout
        networks_response.raise_for_status() # Lança exceção para status HTTP ruins (4xx ou 5xx)
        networks_data = networks_response.json().get('networks', [])
        print(f"DEBUG: Total de redes encontradas globalmente: {len(networks_data)}")
    except requests.exceptions.Timeout:
        print(f"Erro: Timeout ao buscar redes de {API_BASE_URL}.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar redes: {e}")
        return []
    except ValueError: # Erro ao decodificar JSON
        print(f"Erro ao decodificar JSON das redes.")
        return []

    # 2. Filtrar redes em Sorocaba para obter seus IDs
    sorocaba_network_ids = [
        network['id'] for network in networks_data
        if network.get('location', {}).get('city', '').lower() == 'sorocaba'
    ]

    if not sorocaba_network_ids:
        print("DEBUG: Nenhuma rede da CityBik.es encontrada para Sorocaba.")
        return []
    else:
        print(f"DEBUG: IDs das redes encontradas para Sorocaba: {sorocaba_network_ids}")

    # 3. Para cada rede de Sorocaba, buscar suas estações
    for network_id in sorocaba_network_ids:
        specific_network_url = f"{API_BASE_URL}/{network_id}"
        print(f"DEBUG: Buscando estações para a rede: {specific_network_url}")
        try:
            stations_response = requests.get(specific_network_url, timeout=10) # Adiciona timeout
            stations_response.raise_for_status()
            network_detail = stations_response.json().get('network', {})
            
            if network_detail and 'stations' in network_detail:
                stations_for_this_network = network_detail['stations']
                print(f"DEBUG: Encontradas {len(stations_for_this_network)} estações para a rede {network_id}.")
                all_stations_data.extend(stations_for_this_network)
            else:
                print(f"DEBUG: Nenhuma estação encontrada ou estrutura de dados inesperada para a rede {network_id}.")
                # print(f"DEBUG: Detalhes da rede {network_id}: {network_detail}") # Descomente para mais detalhes

        except requests.exceptions.Timeout:
            print(f"Erro: Timeout ao buscar estações para a rede {network_id} de {specific_network_url}.")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar estações para a rede {network_id}: {e}")
        except ValueError: # Erro ao decodificar JSON
            print(f"Erro ao decodificar JSON das estações para a rede {network_id}.")
            
    print(f"DEBUG: Total de estações individuais encontradas em Sorocaba: {len(all_stations_data)}")
    if all_stations_data:
        print(f"DEBUG: Exemplo da primeira estação encontrada: {all_stations_data[0]}") # Mostra a estrutura da primeira estação
    return all_stations_data

# -----------------------------------------------------------------------------
# VIEW PARA EXIBIR O MAPA DIRETAMENTE COMO HTTPRESPONSE
# -----------------------------------------------------------------------------
@login_required
def sorocaba_bike_map_view(request):
    print("--- Executando sorocaba_bike_map_view ---")
    stations = get_actual_bicycle_stations_in_sorocaba(request)
    
    if not stations:
        return HttpResponse("<h1>Nenhuma estação de bicicleta encontrada para Sorocaba na API.</h1>")

    sorocaba_coords = [-23.5017, -47.4581]
    bike_map = folium.Map(location=sorocaba_coords, zoom_start=13, tiles="CartoDB positron")

    marker_cluster = MarkerCluster(name="Estações de Bicicleta").add_to(bike_map)

    print(f"DEBUG (sorocaba_bike_map_view): Adicionando {len(stations)} estações ao mapa...")
    for station in stations:
        name = station.get('name', 'Nome não disponível')
        free_bikes = station.get('free_bikes', 'N/A')
        slots = station.get('empty_slots', 'N/A')
        external_id = station.get('id')  # Obter o ID externo para vincular às avaliações
        lat = station.get('latitude')
        lon = station.get('longitude')

        print(f"DEBUG (sorocaba_bike_map_view): Processando Estação: {name}, Lat: {lat}, Lon: {lon}, Bikes: {free_bikes}, Slots: {slots}")

        if lat is None or lon is None:
            print(f"AVISO (sorocaba_bike_map_view): Coordenadas ausentes para a estação '{name}'. Pulando.")
            continue
        
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (ValueError, TypeError):
            print(f"AVISO (sorocaba_bike_map_view): Coordenadas inválidas para a estação '{name}' (Lat: {lat}, Lon: {lon}). Pulando.")
            continue

        # Buscar avaliações para esta estação
        try:
            bicicletario = Bicicletario.objects.get(external_id=external_id)
            avg_rating = bicicletario.average_rating()
            rating_text = f"<p><strong>Avaliação Média:</strong> {avg_rating} ★</p>" if avg_rating else ""
            avaliar_link = f'<a href="/avaliar/{bicicletario.id}/" target="_blank">Avaliar esta estação</a>'
        except Bicicletario.DoesNotExist:
            avg_rating = None
            rating_text = ""
            avaliar_link = f'<a href="/vincular/{external_id}/" target="_blank">Vincular para avaliar</a>'

        popup_html = f"""
        <div>
            <h4>{name}</h4>
            <p><strong>Bicicletas livres:</strong> {free_bikes}</p>
            <p><strong>Vagas disponíveis:</strong> {slots}</p>
            {rating_text}
            <p>{avaliar_link}</p>
        </div>
        """
        iframe = folium.IFrame(popup_html, width=250, height=150)
        popup = folium.Popup(iframe, max_width=300)

        folium.Marker(
            location=[lat_f, lon_f],
            popup=popup,
            tooltip=name,
            icon=folium.Icon(color='green', icon='bicycle', prefix='fa')
        ).add_to(marker_cluster)

    folium.LayerControl().add_to(bike_map)
    map_html = bike_map._repr_html_()
    return HttpResponse(map_html)

def geocode_cep(cep_string):
    """
    Converte um CEP em coordenadas (latitude, longitude) e endereço usando a API ViaCEP.
    Retorna um dicionário com {'lat': ..., 'lon': ..., 'address': ...} ou None se não encontrado/erro.
    """
    cep_string = cep_string.replace('-', '').replace('.', '').strip()
    if not cep_string.isdigit() or len(cep_string) != 8:
        print(f"DEBUG: Formato de CEP inválido: {cep_string}")
        return None

    VIACEP_URL = f"https://viacep.com.br/ws/{cep_string}/json/"
    print(f"DEBUG: Geocodificando CEP: {cep_string} via {VIACEP_URL}")
    try:
        response = requests.get(VIACEP_URL, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get('erro'):
            print(f"DEBUG: CEP {cep_string} não encontrado pela ViaCEP.")
            return None

        # Nem todos os CEPs retornam lat/lon diretamente via ViaCEP.
        # Precisamos de outra API para geocodificar o endereço se lat/lon não estiverem presentes.
        # Para simplificar aqui, vamos focar nos que retornam ou montar o endereço.
        # A API BrasilAPI pode ser uma alternativa ou Nominatim (requer user-agent).

        # Tentativa de usar BrasilAPI para obter coordenadas se ViaCEP não fornecer
        # (ViaCEP raramente fornece coordenadas diretamente)
        # Vamos precisar do logradouro, cidade, uf para uma busca mais precisa.
        logradouro = data.get('logradouro', '')
        bairro = data.get('bairro', '')
        cidade = data.get('localidade', '')
        uf = data.get('uf', '')
        full_address_for_display = f"{logradouro}, {bairro}, {cidade} - {uf}"
        
        # Usando Nominatim (OpenStreetMap) para geocodificação do endereço
        # É importante definir um User-Agent para o Nominatim
        headers = {'User-Agent': 'MeuAppDjangoDeMapas/1.0 (seuemail@example.com)'} # SEJA GENTIL COM APIS PÚBLICAS
        NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{logradouro}, {cidade}, {uf}",
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        print(f"DEBUG: Buscando coordenadas para '{params['q']}' via Nominatim...")
        geo_response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if geo_data:
            lat = float(geo_data[0].get('lat'))
            lon = float(geo_data[0].get('lon'))
            display_name = geo_data[0].get('display_name')
            print(f"DEBUG: Coordenadas encontradas para CEP {cep_string}: Lat {lat}, Lon {lon} (Endereço: {display_name})")
            return {'lat': lat, 'lon': lon, 'address': display_name, 'cep_address': full_address_for_display}
        else:
            print(f"DEBUG: Não foi possível obter coordenadas para o endereço do CEP {cep_string} via Nominatim.")
            # Retornar apenas o endereço do ViaCEP se não conseguir geocodificar
            return {'lat': None, 'lon': None, 'address': full_address_for_display, 'cep_address': full_address_for_display}

    except requests.exceptions.Timeout:
        print(f"Erro: Timeout ao consultar API de CEP para {cep_string}.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição para geocodificar CEP {cep_string}: {e}")
        return None
    except ValueError: # Erro ao decodificar JSON
        print(f"Erro ao decodificar JSON para CEP {cep_string}.")
        return None


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcula a distância em quilômetros entre dois pontos geográficos (lat/lon).
    """
    R = 6371  # Raio da Terra em km

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def get_route_polyline_osrm(start_lat, start_lon, end_lat, end_lon):
    """
    Obtém uma polilinha de rota entre dois pontos usando o servidor demo do OSRM.
    Retorna uma lista de coordenadas [[lat, lon], ...] ou None.
    """
    # OSRM espera {longitude},{latitude};{longitude},{latitude}
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    OSRM_API_URL = f"http://router.project-osrm.org/route/v1/driving/{coordinates}"
    params = {'overview': 'full', 'geometries': 'geojson'}
    print(f"DEBUG: Buscando rota via OSRM: {OSRM_API_URL} com params {params}")

    try:
        response = requests.get(OSRM_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('routes') and data['routes'][0].get('geometry'):
            # A geometria GeoJSON vem como [lon, lat], precisamos inverter para Folium [lat, lon]
            route_coords_lon_lat = data['routes'][0]['geometry']['coordinates']
            route_coords_lat_lon = [[coord[1], coord[0]] for coord in route_coords_lon_lat]
            print(f"DEBUG: Rota obtida com {len(route_coords_lat_lon)} pontos.")
            return route_coords_lat_lon
        else:
            print(f"DEBUG: Nenhuma rota encontrada ou formato de resposta inesperado do OSRM: {data.get('code')}")
            return None
    except requests.exceptions.Timeout:
        print(f"Erro: Timeout ao consultar API de Rota OSRM.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição para API de Rota OSRM: {e}")
        return None
    except ValueError:
        print(f"Erro ao decodificar JSON da API de Rota OSRM.")
        return None
    

@login_required
def route_to_station_view(request):
    context = {'bike_map_html': None, 'messages': []}
    form_cep = ""

    if request.method == 'POST':
        form_cep = request.POST.get('cep', '').strip()
        context['form_cep'] = form_cep

        if not form_cep:
            context['messages'].append({'type': 'error', 'text': 'Por favor, informe um CEP.'})
        else:
            cep_location_data = geocode_cep(form_cep)

            if not cep_location_data or cep_location_data.get('lat') is None:
                context['messages'].append({'type': 'error', 'text': f"Não foi possível encontrar a localização para o CEP {form_cep}."})
                if cep_location_data and cep_location_data.get('address'):
                     context['messages'].append({'type': 'info', 'text': f"Endereço parcial encontrado: {cep_location_data.get('address')}"})
            else:
                cep_lat = cep_location_data['lat']
                cep_lon = cep_location_data['lon']
                cep_address = cep_location_data.get('address', 'Endereço do CEP não disponível')
                context['cep_address'] = cep_address
                context['cep_coords'] = f"Lat: {cep_lat:.5f}, Lon: {cep_lon:.5f}"

                stations = get_actual_bicycle_stations_in_sorocaba(request)

                if not stations:
                    context['messages'].append({'type': 'warning', 'text': 'Nenhuma estação de bicicleta encontrada em Sorocaba.'})
                else:
                    nearest_station = None
                    min_distance = float('inf')

                    for station in stations:
                        s_lat = station.get('latitude')
                        s_lon = station.get('longitude')
                        if s_lat is not None and s_lon is not None:
                            try:
                                distance = calculate_haversine_distance(cep_lat, cep_lon, float(s_lat), float(s_lon))
                                if distance < min_distance:
                                    min_distance = distance
                                    nearest_station = station
                            except (ValueError, TypeError) as e:
                                print(f"Erro ao calcular distância para estação {station.get('name')}: {e}")
                                continue
                    
                    if nearest_station:
                        context['nearest_station_name'] = nearest_station.get('name')
                        context['nearest_station_distance'] = f"{min_distance:.2f} km"
                        context['nearest_station_bikes'] = nearest_station.get('free_bikes', 'N/A')
                        context['nearest_station_slots'] = nearest_station.get('empty_slots', 'N/A')

                        ns_lat = float(nearest_station['latitude'])
                        ns_lon = float(nearest_station['longitude'])
                        external_id = nearest_station['id']

                        # -------- INÍCIO DA CORREÇÃO --------
                        bicicletario_obj = None  # Inicializa a variável do objeto Bicicletario
                        avg_rating = None      # Inicializa avg_rating

                        # Buscar avaliações para a estação mais próxima
                        try:
                            bicicletario_obj = Bicicletario.objects.get(external_id=external_id)
                            avg_rating = bicicletario_obj.average_rating()
                            context['nearest_station_rating'] = avg_rating
                        except Bicicletario.DoesNotExist:
                            context['nearest_station_rating'] = None
                            # avg_rating permanece None, bicicletario_obj permanece None

                        # Criar o mapa
                        map_center_lat = (cep_lat + ns_lat) / 2
                        map_center_lon = (cep_lon + ns_lon) / 2
                        bike_map = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=14)

                        # Adicionar avaliação ao popup da estação
                        rating_text = f"<br><strong>Avaliação Média:</strong> {avg_rating} ★" if avg_rating is not None else ""
                        
                        if bicicletario_obj: # Se o bicicletário existe no banco de dados
                            url_avaliar = reverse('avaliar_bicicletario', args=[bicicletario_obj.id])
                            avaliar_link = f'<br><a href="{url_avaliar}" target="_blank">Avaliar esta estação</a>'
                        else: # Se o bicicletário não existe (precisa ser vinculado)
                            url_vincular = reverse('vincular_bicicletario', args=[external_id])
                            avaliar_link = f'<br><a href="{url_vincular}" target="_blank">Vincular para avaliar</a>'
                        # -------- FIM DA CORREÇÃO --------

                        popup_station_html = f"""
                        <b>{nearest_station.get('name')} (Mais Próxima)</b><br>
                        Distância: {min_distance:.2f} km<br>
                        Bicicletas Livres: {nearest_station.get('free_bikes', 'N/A')}<br>
                        Vagas Livres: {nearest_station.get('empty_slots', 'N/A')}
                        {rating_text}
                        {avaliar_link}
                        """
                        folium.Marker(
                            location=[ns_lat, ns_lon],
                            popup=folium.Popup(popup_station_html, max_width=300),
                            tooltip=nearest_station.get('name'),
                            icon=folium.Icon(color='green', icon='bicycle', prefix='fa')
                        ).add_to(bike_map)
                        
                        # Obter e desenhar a rota
                        route_polyline = get_route_polyline_osrm(cep_lat, cep_lon, ns_lat, ns_lon)
                        if route_polyline:
                            folium.PolyLine(
                                locations=route_polyline,
                                color='blue',
                                weight=5,
                                opacity=0.7,
                                tooltip="Rota para a estação mais próxima"
                            ).add_to(bike_map)
                            # Ajustar limites do mapa para incluir a rota
                            bike_map.fit_bounds([[min(cep_lat, ns_lat), min(cep_lon, ns_lon)], 
                                                 [max(cep_lat, ns_lat), max(cep_lon, ns_lon)]])
                        else:
                            context['messages'].append({'type': 'warning', 'text': 'Não foi possível traçar a rota.'})
                        
                        context['bike_map_html'] = bike_map._repr_html_()
                    else:
                        context['messages'].append({'type': 'warning', 'text': 'Não foi possível determinar a estação mais próxima.'})
    else: # GET request
        context['messages'].append({'type': 'info', 'text': 'Digite um CEP para encontrar a bicicletaria mais próxima e a rota.'})

    return render(request, 'localizaja/route_to_station.html', context)



def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)  # Agora a função correta será usada
            return redirect('home')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')

    return render(request, 'login.html')

def logout_view(request):
       logout(request)
       return redirect('login')

@login_required
def vincular_bicicletario(request, external_id):
    station = get_actual_bicycle_stations_in_sorocaba(request)
    # Encontrar a estação pelo external_id
    matching_station = next((s for s in station if s['id'] == external_id), None)
    if not matching_station:
        messages.error(request, "Estação não encontrada.")
        return redirect('home')

    # Criar ou obter o bicicletario
    bicicletario, created = Bicicletario.objects.get_or_create(
        external_id=external_id,
        defaults={
            'name': matching_station['name'],
            'latitude': matching_station['latitude'],
            'longitude': matching_station['longitude']
        }
    )

    UserBicicletario.objects.get_or_create(user=request.user, bicicletario=bicicletario)
    messages.success(request, f"{bicicletario.name} vinculado com sucesso!")
    return redirect('home')

# views.py
@login_required
def avaliar_bicicletario(request, bicicletario_id):
    bicicletario = get_object_or_404(Bicicletario, id=bicicletario_id)
    
    if request.method == 'POST':
        form = BicicletarioRatingForm(request.POST)
        if form.is_valid():
            # Verifica se o usuário já avaliou esta estação
            existing_rating = BicicletarioRating.objects.filter(
                user=request.user, 
                bicicletario=bicicletario
            ).first()
            
            if existing_rating:
                # Atualiza avaliação existente
                existing_rating.value = form.cleaned_data['value']
                existing_rating.comment = form.cleaned_data['comment']
                existing_rating.save()
                messages.success(request, "Avaliação atualizada com sucesso!")
            else:
                # Cria nova avaliação
                rating = form.save(commit=False)
                rating.user = request.user
                rating.bicicletario = bicicletario
                rating.save()
                messages.success(request, "Avaliação registrada com sucesso!")
                
            return redirect('rota_para_estacao')
    else:
        # Tenta carregar avaliação existente do usuário
        existing_rating = BicicletarioRating.objects.filter(
            user=request.user, 
            bicicletario=bicicletario
        ).first()
        
        if existing_rating:
            form = BicicletarioRatingForm(instance=existing_rating)
        else:
            form = BicicletarioRatingForm()

    return render(request, 'localizaja/avaliar_bicicletario.html', {
        'form': form, 
        'bicicletario': bicicletario
    })
