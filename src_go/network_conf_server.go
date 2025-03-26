package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/bigkevmcd/go-configparser"
)

const VERSION = "1.0"
const DEFAULT_CONFIG_FILE = "network-configuration.default.conf"
const STATIC_CONTENT_PATH = "static"

type NetworkConfigurationService struct {
	manager           *InterfaceManager
	port              int
	address           string
	apHideInUI        bool
	apInterface       string
	reverseProxyPath  string
	startServer       bool
}

func (n *NetworkConfigurationService) StartServer() {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, fmt.Sprintf("%s/index.html", STATIC_CONTENT_PATH))
	})

	http.HandleFunc("/api/status", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(n.manager.GetStatus())
	})

	http.HandleFunc("/api/config", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			conf := n.manager.GetConf()
			if n.apHideInUI {
				delete(conf, n.apInterface)
			}
			json.NewEncoder(w).Encode(conf)
		} else if r.Method == http.MethodPost {
			var config map[string]interface{}
			if err := json.NewDecoder(r.Body).Decode(&config); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
			log.Printf("Received config: %v", config)
			n.manager.LoadConfig(config)
			w.Write([]byte("OK"))
		}
	})

	http.HandleFunc("/api/interfaces", func(w http.ResponseWriter, r *http.Request) {
		var interfaces []string
		for _, iface := range n.manager.Interfaces {
			if n.apHideInUI && iface.Device == n.apInterface {
				continue
			}
			interfaces = append(interfaces, iface.Device)
		}
		json.NewEncoder(w).Encode(interfaces)
	})

	address := fmt.Sprintf("%s:%d", n.address, n.port)
	log.Printf("Starting server on %s", address)
	if err := http.ListenAndServe(address, nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

func main() {
	var configurationFile = flag.String("c", DEFAULT_CONFIG_FILE, "Configuration file")
	flag.Parse()

	p, err := configparser.NewConfigParserFromFile(configurationFile)
	if err != nil {
		log.Fatalf("Failed to load config (%v): %v", configurationFile, err)
	}

	port, _ := p.GetInt("Server", "Port")
	address, _ := p.Get("Server", "Address")
	startServer, _ := p.GetBool("Server", "EnableServer")
	apHideInUI, _ := p.GetBool("AP", "APHideInUI")
	apInterface := p.Get("AP", "APInterfaceDevice")
	reverseProxyPath := p.Get("Server", "ReverseProxyPath")

	service := NetworkConfigurationService{
		manager: &InterfaceManager{},
		port:              port,
		address:           address,
		apHideInUI:        apHideInUI,
		apInterface:       apInterface,
		reverseProxyPath:  reverseProxyPath,
		startServer:       startServer,
	}

	if startServer {
		service.StartServer()
	} else {
		log.Println("Server disabled, sleeping indefinitely...")
		for {
			time.Sleep(100 * time.Second)
		}
	}
}
