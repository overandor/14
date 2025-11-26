contract ERC20:
    name: string = "Token"
    symbol: string = "TKN"
    totalSupply: uint256 = 1000000
    balances: mapping[address,uint256]
    def transfer(to: address, amount: uint256):
        assert self.balances[msg.sender] >= amount
        self.balances[msg.sender] = self.balances[msg.sender] - amount
        self.balances[to] = self.balances[to] + amount
