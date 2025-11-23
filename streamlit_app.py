import streamlit as st
import asyncio
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
from whirlpools_sdk import WhirlpoolContext, build_whirlpool_client, Percentage  # Note: pip install whirlpools-sdk in requirements.txt
import httpx
import time
import random  # For demo placeholders

# === CONFIG ===
st.set_page_config(page_title="Solana LP Tracker", layout="wide", initial_sidebar_state="expanded")
st.title("🚀 Solana Concentrated Liquidity Tracker")
st.markdown("**Track Orca & Raydium positions** by pasting public wallet addresses. No wallet connection needed!")

# RPC: Use Helius free tier (sign up at helius.dev for key) or fallback
RPC_URL = st.text_input("Solana RPC URL (Helius recommended)", value="https://api.mainnet-beta.solana.com", help="Get free key: helius.dev")
JUPITER_PRICE = "https://price.jup.ag/v6/price?ids="

# Session state for addresses
if "addresses" not in st.session_state:
    st.session_state.addresses = []

# Sidebar: Add/Remove Addresses
with st.sidebar:
    st.header("📝 Wallet Addresses")
    new_addr = st.text_input("Paste Solana address", placeholder="e.g., 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU (test Orca wallet)")
    if st.button("➕ Add Address", type="primary") and new_addr.strip():
        trimmed = new_addr.strip()
        if len(trimmed) == 44 and not any(addr['full'] == trimmed for addr in st.session_state.addresses):  # Basic validation
            st.session_state.addresses.append({'full': trimmed, 'short': trimmed[:8] + "..." + trimmed[-4:]})
            st.success(f"Added {trimmed[:8]}...")
            st.rerun()
        else:
            st.error("Invalid address or duplicate.")

    if st.session_state.addresses:
        st.subheader("Active Wallets")
        for i, addr in enumerate(st.session_state.addresses):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code(addr['short'])
            if col2.button("🗑️", key=f"del_{i}"):
                st.session_state.addresses.pop(i)
                st.rerun()

# === Fetch Logic (Simplified for Demo; Expand with Full SDK) ===
@st.cache_data(ttl=30)  # Refresh every 30s
def fetch_positions(addresses):
    positions = []
    for addr_info in addresses:
        addr_str = addr_info['full']
        try:
            # Mock real fetch (replace with full Whirlpool SDK call)
            # In production: Use AsyncClient + WhirlpoolContext.get_owner_positions(PublicKey(addr_str))
            num_pos = random.randint(0, 3)  # Simulate 0-3 positions per wallet
            for _ in range(num_pos):
                positions.append({
                    'wallet': addr_info['short'],
                    'dex': random.choice(['Orca', 'Raydium']),
                    'pair': f"{random.choice(['SOL', 'USDC', 'ETH'])}/{random.choice(['USDC', 'SOL', 'JUP'])}",
                    'in_range': random.uniform(0, 100),
                    'fees_usd': random.uniform(0.5, 50),
                    'il_percent': round(random.uniform(-15, 5), 2),
                    'efficiency_x': round(random.uniform(5, 25), 1),
                    'value_usd': random.uniform(100, 5000)
                })
        except Exception as e:
            st.error(f"Error fetching {addr_str[:8]}...: {e}")
    return positions

# === Main Dashboard ===
if not st.session_state.addresses:
    st.info("👆 Add a Solana wallet address in the sidebar to start tracking positions.")
    st.markdown("**Test with this public Orca example:** `7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`")
else:
    with st.spinner("🔄 Fetching positions from Orca/Raydium..."):
        positions = fetch_positions(st.session_state.addresses)

    if not positions:
        st.warning("No positions found. Try a wallet with active CLMM liquidity.")
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
                    progress_color = "inverse" if pos['in_range'] > 50 else "off"
                    st.progress(pos['in_range'] / 100, text=None)
                
                # Value & Fees
                with col3:
                    st.metric("Position Value", f"${pos['value_usd']:,.0f}")
                    st.metric("Unclaimed Fees", f"${pos['fees_usd']:,.2f}")
                
                # Bottom Metrics Row
                col4, col5, col6 = st.columns(3)
                with col4:
                    st.metric("Impermanent Loss", f"{pos['il_percent']:.2f}%", delta=None, delta_color="inverse" if pos['il_percent'] > 0 else "normal")
                with col5:
                    st.metric("Capital Efficiency", f"{pos['efficiency_x']}×")
                with col6:
                    if st.button("🌾 Harvest Fees", key=f"harvest_{random.random()}"):
                        st.success("Harvest simulated! (Add tx signing for real.)")
                
                st.divider()

    # Auto-refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Footer
with st.expander("ℹ️ About & Upgrades"):
    st.markdown("""
    - **Current:** Demo mode with mock data. Real Orca fetch coming next.
    - **Next:** Add Raydium, Jupiter Perps, Helius RPC integration.
    - **Tech:** Built with Streamlit + Solana SDK. Free forever!
    """)
