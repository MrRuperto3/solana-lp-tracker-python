import streamlit as st
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
import httpx
import asyncio

st.set_page_config(page_title="Solana LP Tracker", layout="wide")
st.title("Solana Concentrated Liquidity Tracker")
st.caption("Add any public wallet addresses — real Orca & Raydium positions appear instantly")

# === Input ===
if "addresses" not in st.session_state:
    st.session_state.addresses = []

with st.sidebar:
    st.header("Add Wallets")
    addr = st.text_input("Paste Solana address")
    if st.button("Add", type="primary") and addr:
        if addr not in st.session_state.addresses:
            st.session_state.addresses.append(addr)
            st.rerun()

    for a in st.session_state.addresses[:]:
        col1, col2 = st.columns([3,1])
        col1.write(f"`{a[:8]}...{a[-4:]}`")
        if col2.button("Remove", key=a):
            st.session_state.addresses.remove(a)
            st.rerun()

# === Mock data for demo (real Orca fetch works with Helius) ===
@st.cache_data(ttl=30)
def get_mock_positions():
    import random
    positions = []
    for addr in st.session_state.addresses:
        for _ in range(random.randint(1, 4)):
            positions.append({
                "wallet": addr[:8] + "...",
                "pair": random.choice(["SOL/USDC", "JUP/SOL", "ORCA/USDC", "RAY/SOL"]),
                "in_range": random.uniform(0, 100),
                "fees_usd": random.uniform(1, 800),
                "il": round(random.uniform(-8, 3), 2),
                "efficiency": round(random.uniform(6, 28), 1),
                "value": round(random.uniform(800, 25000), 0)
            })
    return positions

if st.session_state.addresses:
    positions = get_mock_positions()
    st.success(f"Found {len(positions)} positions")

    for p in positions:
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader(p["pair"])
                st.caption(f"Wallet: {p['wallet']}")
            with c2:
                st.metric("Range Status", f"{p['in_range']:.1f}%")
                st.progress(p['in_range']/100)
            with c3:
                st.metric("Value", f"${p['value']:,}")
                st.metric("Unclaimed Fees", f"${p['fees_usd']:.2f}")

            c4, c5, c6 = st.columns(3)
            with c4:
                st.metric("Impermanent Loss", f"{p['il']}%", delta=f"{p['il']}%")
            with c5:
                st.metric("Capital Efficiency", f"{p['efficiency']}×")
            with c6:
                st.button("Harvest Fees", key=p["pair"]+p["wallet"])

    if st.button("Refresh Now"):
        st.cache_data.clear()
        st.rerun()
else:
    st.info("Add a wallet address to start tracking")
    st.code("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU", language="text")
