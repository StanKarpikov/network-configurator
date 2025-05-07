use actix_files::{NamedFile, Files};
use actix_web::{error::ErrorBadRequest, get, post, web::{Data, Json}, App, Error, HttpResponse, HttpServer, Responder};
use config::{Config, FileFormat, ConfigError};
use log::info;
use clap::{Command, Arg};
use serde_json::Value;
use std::{path::{Path, PathBuf}, sync::Arc};
use tokio::signal;
use thiserror::Error;
use std::panic;
use std::process;

mod interface_manager;
use interface_manager::interface_manager::InterfaceManager;

const DEFAULT_CONFIG: &str = "network-configuration.default.conf";

struct WEBParameters {
    start_server: bool,
    port: u16,
    address: String,
    ap_hide_in_ui: bool,
    ap_interface: String,
    reverse_proxy_path: String,
}

#[derive(Error, Debug)]
pub enum ParametersInitError {
    #[error("Configuration error: {0}")]
    Config(#[from] ConfigError),
    #[error("Unknown parameters initialisation error")]
    Unknown,
}

impl WEBParameters {
    fn new(def_config: &Config)-> Result<Self, ParametersInitError> {
        let start_server: bool = def_config.get("Server.EnableServer")?;
        let port: u16 = def_config.get("Server.Port")?;
        let address: String = def_config.get("Server.Address")?;
        let ap_hide_in_ui: bool = def_config.get("AP.APHideInUI")?;
        let ap_interface: String = def_config.get("AP.APInterfaceDevice")?;
        let reverse_proxy_path: String = def_config.get("Server.ReverseProxyPath")?;
        Ok(Self {
            start_server,
            port,
            address,
            ap_hide_in_ui,
            ap_interface,
            reverse_proxy_path,
        })
    }
}

#[get("/")]
async fn index() -> impl Responder {
    let path: PathBuf = Path::new("static").join("index.html");
    NamedFile::open(path).map_err(|e| {
        actix_web::error::ErrorInternalServerError(format!("File not found: {}", e))
    })
}

#[get("/api/status")]
async fn get_status(manager: Data<Arc<InterfaceManager>>) -> Result<HttpResponse, Error> {
    let status = manager.get_status().map_err(|e| {
        actix_web::error::ErrorInternalServerError(format!("Failed to get status: {}", e))
    })?;
    Ok(HttpResponse::Ok().json(status))
}

#[get("/api/config")]
async fn get_config(manager: Data<Arc<InterfaceManager>>) -> Result<HttpResponse, Error> {
    let config = manager.get_conf().map_err(|e| {
        actix_web::error::ErrorInternalServerError(format!("Failed to get config: {}", e))
    })?;
    Ok(HttpResponse::Ok().json(config))
}

#[post("/api/config")]
async fn post_config(manager: Data<Arc<InterfaceManager>>, config: Json<serde_json::Value>) -> Result<HttpResponse, Error> {
    if let Value::Object(map) = config.into_inner() {
        manager.load_config(map).map_err(|e| {
            actix_web::error::ErrorInternalServerError(format!("Failed to load config: {}", e))
        })?;
        Ok(HttpResponse::Ok().into())
    } else {
        Err(ErrorBadRequest("Expected a JSON object"))
    }
}

#[get("/api/interfaces")]
async fn get_interfaces(manager: Data<Arc<InterfaceManager>>, parameters: Data<Arc<WEBParameters>>) -> Result<HttpResponse, Error> {
    let mut interfaces = Vec::new();
    match manager.get_interfaces() {
        Ok(interface_list) => {
            for interface in interface_list {
                if parameters.ap_hide_in_ui && interface.device == parameters.ap_interface {
                    continue; // Skip the interface if we need to hide it
                }
                interfaces.push(interface.device.clone());
            }
            Ok(HttpResponse::Ok().json(interfaces))
        }
        Err(e) => {
            Err(actix_web::error::ErrorInternalServerError(format!("Failed to load interfaces: {}", e)))
        }
    }
}

#[get("/api/{interface_id}/config")]
async fn interface_config(manager: Data<Arc<InterfaceManager>>, interface_id: String) -> Result<HttpResponse, Error> {
    let config = manager.get_conf().map_err(|e| {
        actix_web::error::ErrorInternalServerError(format!("Failed to get config: {}", e))
    })?;
    Ok(HttpResponse::Ok().json(config[&interface_id].clone()))
}

#[allow(unused_variables)]
async fn run(parameters:Arc<WEBParameters>, manager: Arc<InterfaceManager>) -> std::io::Result<()> {
    if parameters.start_server {
        let server_string = format!("{}{}", parameters.address, parameters.port);
        info!("Starting server on http://{}", server_string);
        HttpServer::new(move || {
            App::new()
                .app_data(Data::new(manager.clone()))
                .app_data(Data::new(parameters.clone()))
                .service(Files::new("/static", "static").prefer_utf8(true))
                .service(index)
                .service(get_status)
                .service(get_config)
                .service(post_config)
                .service(get_interfaces)
                .service(interface_config)
        })
            .bind(server_string)?
            .run()
            .await
    }else{
        info!("Waiting indefinitely...");
        signal::ctrl_c().await?;
        info!("Received Ctrl+C, exiting...");
        Ok(())
    }
}

fn set_custom_panic_handler() {
    panic::set_hook(Box::new(|panic_info| {
        let location = panic_info.location().map_or_else(|| "unknown location".to_string(), |loc| {
            format!("{}:{}", loc.file(), loc.line())
        });
        
        let payload_message = if let Some(s) = panic_info.payload().downcast_ref::<&str>() {
            s.to_string()  // If payload is a string slice, use it
        } else if let Some(s) = panic_info.payload().downcast_ref::<String>() {
            s.clone()  // If payload is a String, clone it
        } else {
            "Non-string panic payload".to_string()  // Handle other types of payloads
        };

        let panic_message = format!(
            "Panic occurred at {}.\nDetails: {}\n",
            location,
            payload_message
        );
        
        println!("{}", panic_message);
        process::exit(1);
    }));
}

//noinspection HttpUrlsUsage
#[actix_web::main]
async fn main() -> std::io::Result<()> {

    // set_custom_panic_handler();

    let matches = Command::new(clap::crate_name!())
        .author(clap::crate_authors!())
        .about(clap::crate_description!())
        .version(clap::crate_version!())
        .arg(
            Arg::new("conf")
                .short('c')
                .long("config")
                .required(false)
                .help("Configuration file"),
        )
        .get_matches();

    let config_file: Option<String> = matches.get_one::<String>("conf").cloned();

    let mut config_builder = Config::builder()
        .add_source(config::File::new(DEFAULT_CONFIG, FileFormat::Ini));

    if let Some(config_path) = config_file {
        config_builder = config_builder.add_source(config::File::new(&config_path, FileFormat::Ini).required(false));
    }
    
    let def_config = match config_builder.build() {
        Ok(cfg) => cfg,
        Err(e) => {
            eprintln!("Failed to read configuration: {}", e);
            std::process::exit(1);
        }
    };

    let web_parameters = WEBParameters::new(&def_config).expect("Failed to load configuration");
    let manager = InterfaceManager::new(&def_config)?;
    run(Arc::new(web_parameters), Arc::new(manager)).await?;

    Ok(())
}
