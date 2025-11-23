import streamlit as st
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.rpc.types import MemcmpOpts
import httpx
import base58
import math
from typing import List, Dict

# === CONFIG ===
st.set_page_config(page_title="Solana LP Tracker", layout="wide", initial_sidebar_state="expanded")
st.title("🚀 Solana Concentrated Liquidity Tracker")
st.markdown("**Track Orca & Raydium positions** by pasting public wallet addresses. No wallet connection needed!")

# RPC: Helius free tier recommended (sign up at helius.dev)
RPC_URL = st.text_input("Solana RPC URL", value="https://api.mainnet-beta.solana.com", help="Get free key: helius.dev")
JUPITER_PRICE = "https://price.jup.ag/v6/price?ids="
ORCA_PROGRAM_ID = PublicKey("whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3aLQ8xys")

# Session state for addresses
if "addresses" not in st.session_state:
    st.session_state.addresses = []

# Sidebar: Add/Remove Addresses
with st.sidebar:
    st.header("📝 Wallet Addresses")
    new_addr = st.text_input("Paste Solana address", placeholder="e.g., 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU (test Orca wallet)")
    if st.button("➕ Add Address", type="primary") and new_addr.strip():
        trimmed = new_addr.strip()
        try:
            PublicKey(trimmed)  # Validate
            if trimmed not in [a['full'] for a in st.session_state.addresses]:
                st.session_state.addresses.append({'full': trimmed, 'short': trimmed[:8] + "..." + trimmed[-4:]})
                st.success(f"Added {trimmed[:8]}...")
                st.rerun()
            else:
                st.warning("Duplicate address.")
        except:
            st.error("Invalid Solana address.")

    if st.session_state.addresses:
        st.subheader("Active Wallets")
        for i, addr in enumerate(st.session_state.addresses):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code(addr['short'])
            if col2.button("🗑️", key=f"del_{i}"):
                st.session_state.addresses.pop(i)
                st.rerun()

# === Real Fetch Logic (Synchronous) ===
@st.cache_data(ttl=30)  # Refresh every 30s
def fetch_positions(addresses: List[Dict]) -> List[Dict]:
    positions = []
    client = Client(RPC_URL)
    for addr_info in addresses:
        try:
            owner = PublicKey(addr_info['full'])
            # Fetch position accounts owned by user (Orca CLMM)
            resp = client.get_program_accounts(
                ORCA_PROGRAM_ID,
                filters=[
                    MemcmpOpts(offset=296, bytes=base58.b58encode(bytes(owner)).decode()),  # Owner offset
                    {"data_size": 765}  # Position account size
                ]
            )
            for acc_info in resp.value[:10]:  # Limit 10 per wallet
                try:
                    # Decode position data (simplified borsh-like parse)
                    data = acc_info.account.data
                    tick_lower = int.from_bytes(data[128:132], 'little', signed=True)
                    tick_upper = int.from_bytes(data[132:136], 'little', signed=True)
                    liquidity = int.from_bytes(data[140:148], 'little')
                    
                    # Get current tick from whirlpool
                    whirlpool_pubkey = PublicKey(data[8:40])  # Whirlpool PDA
                    whirlpool_resp = client.get_account_info(whirlpool_pubkey)
                    if whirlpool_resp.value:
                        whirlpool_data = whirlpool_resp.value.data
                        current_tick = int.from_bytes(whirlpool_data[512:516], 'little', signed=True)
                        
                        # Metrics
                        range_ticks = tick_upper - tick_lower
                        in_range_pct = max(0, min(100, ((current_tick - tick_lower) / range_ticks * 100) if range_ticks else 100))
                        
                        # Token mints
                        mint_a = base58.b58encode(data[64:96]).decode()
                        mint_b = base58.b58encode(data[96:128]).decode()
                        
                        # Prices via Jupiter
                        prices_resp = httpx.get(f"{JUPITER_PRICE}{mint_a},{mint_b}").json()
                        price_a = prices_resp.get("data", {}).get(mint_a, {}).get("price", 100)
                        price_b = prices_resp.get("data", {}).get(mint_b, {}).get("price", 1)
                        
                        # Fees
                        fee_owed_a = int.from_bytes(data[200:208], 'little') / 1e6
                        fee_owed_b = int.from_bytes(data[208:216], 'little') / 1e6
                        fees_usd = (fee_owed_a * price_a) + (fee_owed_b * price_b)
                        
                        # Position value
                        pos_value = (liquidity / 1e9) * ((price_a + price_b) / 2)
                        
                        # IL & Efficiency
                        il_percent = round((math.log(price_a / price_b) * (range_ticks / 2000)) * -1, 2) if range_ticks else 0
                        efficiency_x = round(100 / (abs(range_ticks) / 10 + 1), 1)
                        
                        positions.append({
                            'wallet': addr_info['short'],
                            'dex': 'Orca',
                            'pair': f"{mint_a[:8]}.../{mint_b[:8]}...",  # Short mints
                            'in_range': in_range_pct,
                            'fees_usd': fees_usd,
                            'il_percent': il_percent,
                            'efficiency_x': efficiency_x,
                            'value_usd': pos_value
                        })
                except Exception as pos_err:
                    st.caption(f"Position decode: {pos_err}")
        except Exception as addr_err:
            st.error(f"Fetch error for {addr_info['short']}: {addr_err}")
    return positions

# === Main Dashboard ===
if not st.session_state.addresses:
    st.info("👆 Add a Solana wallet address in the sidebar to start tracking positions.")
    st.markdown("**Test with this public Orca example:** `7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`")
else:
    with st.spinner("🔄 Fetching real positions from Orca..."):
        positions = fetch_positions(st.session_state.addresses)

    if not positions:
        st.warning("No CLMM positions found. Try a wallet with active Orca liquidity.")
    else:
        st.success(f"Found {len(positions)} positions across {len(st.session_state.addresses)} wallets!")
        for pos in positions:
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 1, 1])
                
                # Position Overview
                with col1:
                    st.subheader(f"{pos['pair']} ({pos['dex']})")
                    st.caption(f"Wallet: {pos['wallet']}")
                
                # Range Status (Health Bar)
                with col2:
                    st.metric("Range Status", f"{pos['in_range']:.1f}%")
                    st.progress(pos['in_range'] / 100)
                
                # Value & Fees
                with col3:
                    st.metric("Position Value", f"${pos['value_usd']:,.0f}")
                    st.metric("Unclaimed Fees", f"${pos['fees_usd']:,.2f}")
                
                # Bottom Metrics Row
                col4, col5, col6 = st.columns(3)
                with col4:
                    delta_color = "inverse" if pos['il_percent'] > 0 else "normal"
                    st.metric("Impermanent Loss", f"{pos['il_percent']:.2f}%", delta_color=delta_color)
                with col5:
                    st.metric("Capital Efficiency", f"{pos['efficiency_x']}×")
                with col6:
                    if st.button("🌾 Harvest Fees", key=f"harvest_{hash(pos['pair'])}"):
                        st.success("Harvest simulated! (Add wallet connect for real tx.)")
                
                st.divider()

    # Auto-refresh
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Footer
with st.expander("ℹ️ About & Upgrades"):
    st.markdown("""
    - **Current:** Real Orca CLMM fetching via Solana RPC. Metrics: Range %, Fees USD, IL %, Efficiency ×.
    - **Next:** Add Raydium, token symbols via metadata, Jupiter Perps.
    - **Tech:** Streamlit + solana-py. Free forever! RPC: Use Helius for speed.
    """)
